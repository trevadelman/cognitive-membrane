"""
macOS-specific Keyboard Monitor Implementation

This module implements keyboard event monitoring for macOS using the Quartz framework.
It captures global keyboard events and translates them into our KeyboardEvent format.
"""

import asyncio
import threading
from datetime import datetime
from typing import Dict, Optional, Set

from Quartz import (
    CGEventGetFlags,
    CGEventGetIntegerValueField,
    kCGHeadInsertEventTap,
    kCGEventTapOptionDefault,
    kCGKeyboardEventKeycode,
    CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource,
    CFRunLoopGetCurrent,
    CFRunLoopRun,
    CFRunLoopStop,
    CGEventMaskBit,
    CGEventTapCreate,
    CGEventTapEnable,
    kCFRunLoopCommonModes,
    kCGEventFlagMaskShift,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskCommand,
    kCGEventKeyDown,
    kCGEventKeyUp,
    kCGEventMaskForAllEvents,
    kCGSessionEventTap
)

from .keyboard_monitor import KeyboardEvent, KeyboardMonitor

# Mapping of modifier flag masks to our modifier key names
MODIFIER_MAP = {
    kCGEventFlagMaskShift: 'shift',
    kCGEventFlagMaskControl: 'ctrl',
    kCGEventFlagMaskAlternate: 'alt',
    kCGEventFlagMaskCommand: 'meta'
}

class MacOSKeyboardMonitor(KeyboardMonitor):
    """macOS-specific implementation of keyboard monitoring."""
    
    def __init__(self):
        """Initialize the macOS keyboard monitor."""
        super().__init__()
        self._event_tap = None
        self._run_loop_source = None
        self._run_loop_thread = None
        self._current_loop = None
        
    def _create_event_callback(self, proxy, event_type, event, refcon):
        """Callback function for keyboard events.
        
        Args:
            proxy: The event tap proxy
            event_type: Type of event (key down/up)
            event: The keyboard event
            refcon: Reference constant (unused)
            
        Returns:
            The event (to allow it to propagate) or None to block it
        """
        try:
            # Get key code and modifiers
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            flags = CGEventGetFlags(event)
            if not isinstance(flags, int):
                flags = 0  # Default to no modifiers if flags is invalid
            
            # Convert to character if possible
            key_char = self._keycode_to_char(keycode, flags)
            if not key_char:
                return event  # Let unknown keys pass through
                
            # Get active modifiers
            modifiers = set()
            for mask, name in MODIFIER_MAP.items():
                if flags & mask:
                    modifiers.add(name)
                    
            # Create timestamp
            timestamp = datetime.now()
            
            # Create keyboard event
            keyboard_event = KeyboardEvent(
                key=key_char,
                event_type='press' if event_type == kCGEventKeyDown else 'release',
                timestamp=timestamp,
                modifiers=modifiers
            )
            
            # Handle key press/release
            if event_type == kCGEventKeyDown:
                if handler := self.handlers.get('press'):
                    handler(keyboard_event)
            elif event_type == kCGEventKeyUp:
                if handler := self.handlers.get('release'):
                    handler(keyboard_event)
                
        except Exception as e:
            print(f"Error in event callback: {e}")
            
        return event  # Let the event propagate to other applications
        
    async def start(self) -> None:
        """Start monitoring keyboard events."""
        if self._is_running:
            return
            
        # Create event tap
        # Create event tap
        mask = CGEventMaskBit(kCGEventKeyDown) | CGEventMaskBit(kCGEventKeyUp)
        self._event_tap = CGEventTapCreate(
            kCGSessionEventTap,      # Tap at session level
            kCGHeadInsertEventTap,   # Insert at start of event chain
            kCGEventTapOptionDefault,
            mask,                    # Event types to monitor
            self._create_event_callback,
            None                     # User data (not needed)
        )
        
        if not self._event_tap:
            raise RuntimeError("Failed to create event tap")
            
        # Create and add run loop source
        self._run_loop_source = CFMachPortCreateRunLoopSource(
            None,
            self._event_tap,
            0
        )
        
        # Store current loop for later use
        self._current_loop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(
            self._current_loop,
            self._run_loop_source,
            kCFRunLoopCommonModes
        )
        
        # Enable the event tap
        CGEventTapEnable(self._event_tap, True)
        
        # Start run loop in a separate thread
        self._run_loop_thread = threading.Thread(target=CFRunLoopRun)
        self._run_loop_thread.start()
        
        self._is_running = True
        
    async def stop(self) -> None:
        """Stop monitoring keyboard events."""
        if not self._is_running:
            return
            
        # Disable event tap
        if self._event_tap:
            CGEventTapEnable(self._event_tap, False)
            
        # Stop run loop
        if self._run_loop_thread and self._run_loop_thread.is_alive():
            if self._current_loop:
                CFRunLoopStop(self._current_loop)
            try:
                self._run_loop_thread.join(timeout=1.0)  # Wait up to 1 second
            except TimeoutError:
                print("Warning: Run loop thread did not stop in time")
            
        self._event_tap = None
        self._run_loop_source = None
        self._run_loop_thread = None
        self._current_loop = None
        self._is_running = False
        
    def _keycode_to_char(self, keycode: int, flags: int) -> Optional[str]:
        """Convert a keycode to a character.
        
        Args:
            keycode: The keyboard event keycode
            flags: Modifier flags
            
        Returns:
            Character representation of the key or None if not mappable
        """
        # Common key mappings
        KEY_MAP = {
            0: 'a', 1: 's', 2: 'd', 3: 'f', 4: 'h',
            5: 'g', 6: 'z', 7: 'x', 8: 'c', 9: 'v',
            11: 'b', 12: 'q', 13: 'w', 14: 'e', 15: 'r',
            16: 'y', 17: 't', 18: '1', 19: '2', 20: '3',
            21: '4', 22: '6', 23: '5', 24: '=', 25: '9',
            26: '7', 27: '-', 28: '8', 29: '0', 30: ']',
            31: 'o', 32: 'u', 33: '[', 34: 'i', 35: 'p',
            37: 'l', 38: 'j', 39: "'", 40: 'k', 41: ';',
            42: '\\', 43: ',', 44: '/', 45: 'n', 46: 'm',
            47: '.', 50: '`',
            # Function keys
            122: 'F1', 120: 'F2', 99: 'F3', 118: 'F4',
            96: 'F5', 97: 'F6', 98: 'F7', 100: 'F8',
            101: 'F9', 109: 'F10', 103: 'F11', 111: 'F12',
            # Special keys
            36: 'Return', 48: 'Tab', 49: 'Space',
            51: 'Delete', 53: 'Escape', 55: 'Command',
            56: 'Shift', 57: 'CapsLock', 58: 'Option',
            59: 'Control', 123: 'Left', 124: 'Right',
            125: 'Down', 126: 'Up'
        }
        
        # Handle shift modifier for common symbols
        SHIFT_MAP = {
            '1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
            '6': '^', '7': '&', '8': '*', '9': '(', '0': ')',
            '-': '_', '=': '+', '[': '{', ']': '}', '\\': '|',
            ';': ':', "'": '"', ',': '<', '.': '>', '/': '?',
            '`': '~'
        }
        
        # Get base character
        char = KEY_MAP.get(keycode)
        if not char:
            return None
            
        # Handle letter case
        if len(char) == 1 and char.isalpha():
            # Check for Shift or CapsLock
            caps_on = bool(flags & (1 << 16))  # CapsLock state
            shift_on = bool(flags & kCGEventFlagMaskShift)
            if caps_on != shift_on:  # One but not both
                char = char.upper()
            else:
                char = char.lower()
        # Handle shifted symbols
        elif len(char) == 1 and char in SHIFT_MAP and bool(flags & kCGEventFlagMaskShift):
            char = SHIFT_MAP[char]
            
        return char
