import os
import hashlib
import binascii
from PySide6.QtCore import QObject, Signal

class EventBus(QObject):
    """Central event bus for cross-component communication in the Firmware Workspace."""
    document_modified = Signal(object) # Document
    selection_changed = Signal(object, int, int) # Document, start, end
    cursor_moved = Signal(object, int) # Document, offset
    bookmarks_changed = Signal(object) # Document
    
# Global event bus instance
event_bus = EventBus()

class FirmwareDocument:
    """Core data model representing a single opened firmware file."""
    
    def __init__(self, file_path=None, data=b""):
        self.file_path = file_path
        self.file_name = os.path.basename(file_path) if file_path else "Untitled"
        self._data = bytearray(data)
        
        self.is_modified = False
        self.is_read_only = False
        
        # Metadata
        self.regions = []
        self.bookmarks = {}  # offset -> {'name': str, 'color': str}
        self.annotations = {}
        
        # History (Undo/Redo)
        self.undo_stack = []
        self.redo_stack = []
        
        # View state (for session recovery)
        self.cursor_offset = 0
        self.selection_start = -1
        self.selection_end = -1
        self.scroll_position = 0
        
        # Statistics & Info
        self.open_time = None
        self._sha256 = None
        self._crc32 = None

    @property
    def data(self):
        return self._data
        
    @property
    def size(self):
        return len(self._data)
        
    def get_byte(self, offset):
        if 0 <= offset < len(self._data):
            return self._data[offset]
        return None

    def edit_byte(self, offset, val):
        if self.is_read_only: return False
        if 0 <= offset < len(self._data):
            old_val = self._data[offset]
            if old_val != val:
                # Add to undo stack (basic implementation)
                self.undo_stack.append({
                    'type': 'edit',
                    'offset': offset,
                    'old_val': old_val,
                    'new_val': val
                })
                self.redo_stack.clear()
                
                self._data[offset] = val
                self.is_modified = True
                event_bus.document_modified.emit(self)
                return True
        return False
        
    def edit_bytes(self, offset, new_bytes):
        if self.is_read_only: return False
        count = len(new_bytes)
        if count <= 0 or offset >= len(self._data): return False
        end = min(offset + count, len(self._data))
        written = end - offset
        
        old_bytes = self._data[offset:end]
        if old_bytes != new_bytes[:written]:
            self.undo_stack.append({
                'type': 'edit_block',
                'offset': offset,
                'old_val': old_bytes,
                'new_val': new_bytes[:written]
            })
            self.redo_stack.clear()
            
            self._data[offset:end] = new_bytes[:written]
            self.is_modified = True
            event_bus.document_modified.emit(self)
            
            if written < count:
                remaining = new_bytes[written:]
                self.insert_bytes(end, remaining)
            return True
        return False
        
    def insert_bytes(self, offset, insert_data):
        if self.is_read_only: return False
        self.undo_stack.append({
            'type': 'insert',
            'offset': offset,
            'length': len(insert_data)
        })
        self.redo_stack.clear()
        self._data[offset:offset] = insert_data
        self.is_modified = True
        event_bus.document_modified.emit(self)
        return True
        
    def remove_bytes(self, offset, count):
        if self.is_read_only: return False
        if offset + count > len(self._data):
            count = len(self._data) - offset
        if count <= 0: return False
        
        removed_data = self._data[offset:offset+count]
        self.undo_stack.append({
            'type': 'remove',
            'offset': offset,
            'old_val': removed_data
        })
        self.redo_stack.clear()
        
        del self._data[offset:offset+count]
        self.is_modified = True
        event_bus.document_modified.emit(self)
        return True

    def get_data_slice(self, start, end):
        return self._data[start:end]
        
    def calculate_hashes(self):
        self._crc32 = hex(binascii.crc32(self._data) & 0xFFFFFFFF)
        self._sha256 = hashlib.sha256(self._data).hexdigest()

    def add_bookmark(self, offset, name, color="#4CAF50"):
        if 0 <= offset < self.size:
            self.bookmarks[offset] = {'name': name, 'color': color}
            event_bus.bookmarks_changed.emit(self)
            return True
        return False
        
    def remove_bookmark(self, offset):
        if offset in self.bookmarks:
            del self.bookmarks[offset]
            event_bus.bookmarks_changed.emit(self)
            return True
        return False
