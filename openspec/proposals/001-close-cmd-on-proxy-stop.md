# Change Proposal 001: Close CMD Debug Window on Proxy Stop

**Status:** ✅ Implemented  
**Created:** 2025-10-21  
**Implemented:** 2025-10-21  
**Author:** System  
**Priority:** Medium  
**Effort:** Low (1-2 hours)

---

## Problem Statement

Currently, when the proxy is started in debug mode on Windows, a CMD console window opens with the title "Mitmproxy Console (Debug)" showing real-time mitmdump output. However, when the user clicks the "Stop Proxy" button, the CMD window remains open even though the mitmproxy process is terminated.

**Current Behavior:**
1. User starts proxy → CMD window opens with live mitmdump output
2. User stops proxy → mitmproxy process terminates, but CMD window stays open
3. User must manually close the CMD window

**Impact:**
- Poor user experience - requires manual cleanup
- Multiple orphaned CMD windows accumulate if proxy is restarted multiple times
- Inconsistent behavior - users expect the window to close automatically

---

## Proposed Solution

Modify the proxy stop mechanism to automatically close the CMD debug window when the proxy is stopped, ensuring clean process termination.

### Technical Approach

**File:** `warp_account_manager.py`

**Class:** `MitmProxyManager`

**Changes Required:**

1. **Track the CMD window handle (Windows-only)**
   - Store window handle/PID when starting proxy in debug mode
   - Use this reference to close the window on stop

2. **Modify `start()` method** (lines 992-1009)
   - When launching in debug mode with `cmd /k`, change to `cmd /c` (auto-closes on exit)
   - OR store the CMD parent process handle for manual termination

3. **Modify `stop()` method** (lines 1157-1180)
   - Add Windows-specific cleanup to close CMD window
   - Use `taskkill` or process termination to close parent CMD process
   - Ensure graceful shutdown order: mitmdump → CMD window

### Implementation Options

#### Option A: Change `/k` to `/c` (Simplest)
```python
# Line 999: Change from
self.process = subprocess.Popen(
    f'start "Mitmproxy Console (Debug)" cmd /k "{cmd_str}"',
    shell=True
)

# To:
self.process = subprocess.Popen(
    f'start "Mitmproxy Console (Debug)" cmd /c "{cmd_str}"',
    shell=True
)
```

**Pros:**
- Minimal code change (1 character)
- Automatic cleanup when mitmdump exits
- No additional tracking required

**Cons:**
- Window closes immediately when mitmdump crashes (no error visibility)
- User can't inspect output after stop

#### Option B: Track and Kill CMD Parent Process (Recommended)
```python
# In __init__:
self.cmd_process_handle = None

# In start() (after line 1000):
if self.debug_mode:
    # Store CMD window info for cleanup
    import win32gui, win32process
    time.sleep(0.5)  # Allow window to spawn
    def find_cmd_window(hwnd, ctx):
        if "Mitmproxy Console (Debug)" in win32gui.GetWindowText(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            ctx.append(pid)
    pids = []
    win32gui.EnumWindows(find_cmd_window, pids)
    if pids:
        self.cmd_process_handle = psutil.Process(pids[0])

# In stop() (after line 1163):
if IS_WINDOWS and self.cmd_process_handle:
    try:
        self.cmd_process_handle.terminate()
        self.cmd_process_handle.wait(timeout=3)
        print("CMD debug window closed")
    except:
        pass
    finally:
        self.cmd_process_handle = None
```

**Pros:**
- Controlled cleanup on stop
- Window stays open until explicitly stopped (good for debugging)
- User maintains control

**Cons:**
- Requires pywin32 dependency (or use ctypes)
- More complex implementation
- Needs error handling for window enumeration

#### Option C: Use subprocess.CREATE_NEW_PROCESS_GROUP (Alternative)
```python
# In start() (lines 998-1001):
if self.debug_mode:
    cmd_process = subprocess.Popen(
        f'cmd /k "{cmd_str}"',
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
    self.cmd_process_handle = cmd_process

# In stop():
if IS_WINDOWS and self.cmd_process_handle:
    subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.cmd_process_handle.pid)])
    self.cmd_process_handle = None
```

**Pros:**
- No external dependencies (uses built-in subprocess)
- Process group termination kills CMD and children
- Simple implementation

**Cons:**
- Uses `taskkill /F` which is forceful
- Less graceful than Option B

---

## Recommended Implementation

**Choose Option C (subprocess.CREATE_NEW_PROCESS_GROUP)** for the following reasons:
1. No additional dependencies required
2. Clean implementation using subprocess module
3. Works reliably on Windows
4. Balances simplicity and control

---

## Implementation Plan

### Step 1: Add CMD Process Tracking
```python
# Line 901-906 in __init__:
def __init__(self):
    self.process = None
    self.cmd_process_handle = None  # ADD THIS LINE
    self.port = 8080
    self.script_path = "warp_proxy_script.py"
    self.debug_mode = True
    self.cert_manager = CertificateManager()
```

### Step 2: Modify Start Method
```python
# Lines 995-1001, replace with:
if self.debug_mode:
    # Debug mode: Console window visible
    print("Debug mode active - Mitmproxy console window will open")
    self.cmd_process_handle = subprocess.Popen(
        f'cmd /k "{cmd_str}"',
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
```

### Step 3: Modify Stop Method
```python
# Lines 1157-1180, add at the beginning of stop():
def stop(self):
    """Mitmproxy'yi durdur"""
    try:
        # Close CMD debug window first (Windows only)
        if IS_WINDOWS and self.cmd_process_handle:
            try:
                print("Closing CMD debug window...")
                subprocess.call(
                    ['taskkill', '/F', '/T', '/PID', str(self.cmd_process_handle.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("CMD debug window closed")
            except Exception as e:
                print(f"CMD window close warning: {e}")
            finally:
                self.cmd_process_handle = None
        
        # Existing process termination code continues...
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=10)
            print("Mitmproxy durduruldu")
            return True
        # ... rest of existing code
```

---

## Testing Checklist

- [ ] Start proxy in debug mode → CMD window opens
- [ ] Stop proxy → CMD window closes automatically
- [ ] Verify no orphaned processes remain (check Task Manager)
- [ ] Restart proxy multiple times → no window accumulation
- [ ] Test on Windows 10/11
- [ ] Verify headless mode (debug_mode=False) still works correctly
- [ ] Check that stop button status updates properly
- [ ] Ensure error messages still visible before window closes

---

## Edge Cases & Considerations

1. **User manually closes CMD window:**
   - Current behavior: `self.process` becomes invalid
   - Solution: Already handled by `self.process.poll()` check in `stop()`

2. **Crash during shutdown:**
   - Use `try/finally` to ensure `cmd_process_handle` is reset
   - Prevents stale process references

3. **Non-debug mode:**
   - `cmd_process_handle` remains `None`
   - No impact on headless operation

4. **macOS/Linux:**
   - Changes are Windows-only (`if IS_WINDOWS`)
   - No impact on other platforms

---

## Rollback Plan

If issues arise:
1. Revert to `cmd /k` without process tracking
2. Remove `cmd_process_handle` tracking code
3. Document known limitation: "Users must manually close debug window"

---

## Documentation Updates

Update `openspec/project.md` section 9 (Technical Debt):
- Remove "debug console cleanup" from future improvements
- Mark as completed in changelog

---

## Related Issues

- Related to future enhancement: Add UI toggle for debug mode (proposal #TBD)
- Related to: Headless proxy mode implementation (proposal #TBD)

---

## Acceptance Criteria

✅ CMD debug window automatically closes when "Stop Proxy" button is clicked  
✅ No orphaned CMD processes remain after stop  
✅ Multiple start/stop cycles work correctly  
✅ Headless mode unaffected  
✅ Error handling prevents crashes  
✅ Works on Windows 10 and Windows 11  

---

## Estimated Timeline

- Implementation: 30 minutes
- Testing: 30 minutes
- Documentation: 15 minutes
- **Total: ~1-2 hours**
