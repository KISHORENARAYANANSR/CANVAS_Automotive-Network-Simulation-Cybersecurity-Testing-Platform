import cantools
import os

DBC_PATH = os.path.join(os.path.dirname(__file__), '..', 'dbc', 'vehicle.dbc')

class CANCodec:
    def __init__(self):
        self.db = cantools.database.load_file(DBC_PATH)

    def encode(self, frame_id_or_name, data_dict):
        """
        Encode a dictionary of signal values into a CAN payload based on DBC.
        Returns exactly 8 bytes.
        """
        try:
            message = self.db.get_message_by_frame_id(frame_id_or_name) if isinstance(frame_id_or_name, int) else self.db.get_message_by_name(frame_id_or_name)
            data = message.encode(data_dict)
            # Strict padding to 8 bytes for CAN 2.0 compliance
            return data.ljust(8, b'\x00')
        except KeyError:
            print(f"Unknown message {frame_id_or_name}")
            return b'\x00' * 8
        except Exception as e:
            print(f"Encode error {frame_id_or_name}: {e}")
            return b'\x00' * 8

    def decode(self, frame_id, data_bytes):
        """
        Decode a CAN payload back into a dictionary of signal values.
        Handles padding correctly by using the DBC message definition.
        """
        try:
            message = self.db.get_message_by_frame_id(frame_id)
            # cantools decode will only use the bits defined in the DBC
            return message.decode(data_bytes, decode_choices=False)
        except KeyError:
            return None
        except Exception as e:
            print(f"Decode error {frame_id}: {e}")
            return None

# Singleton instance
codec = CANCodec()
