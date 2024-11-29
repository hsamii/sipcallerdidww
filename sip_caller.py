import pjsua as pj
import wave
import time
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Logging callback
def log_cb(level, msg, length):
    try:
        print(msg.decode('utf-8'))
    except UnicodeDecodeError:
        print("Logging error: Unable to decode message.")

# Call state callback
class CallCallback(pj.CallCallback):
    def __init__(self, call=None):
        super().__init__(call)
        self.recorder_id = None
        self.recording_filename = None

    def on_state(self):
        print(f"Call state: {self.call.info().state_text}")
        if self.call.info().state == pj.CallState.DISCONNECTED:
            if self.recorder_id is not None:
                try:
                    lib.recorder_destroy(self.recorder_id)
                    print(f"Recorder destroyed for: {self.recording_filename}")
                except pj.Error as e:
                    print(f"Error destroying recorder: {str(e)}")
                self.recorder_id = None

    def on_media_state(self):
        if self.call.info().media_state == pj.MediaState.ACTIVE:
            call_slot = self.call.info().conf_slot
            try:
                # Create recordings directory if it doesn't exist
                if not os.path.exists("recordings"):
                    os.makedirs("recordings")
                
                # Generate recording filename
                self.recording_filename = os.path.join(
                    "recordings",
                    f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                )
                
                # Create recorder and connect call slot to recorder slot
                self.recorder_id = lib.create_recorder(self.recording_filename)
                rec_slot = lib.recorder_get_slot(self.recorder_id)
                lib.conf_connect(call_slot, rec_slot)
                print(f"Recording started: {self.recording_filename}")
            except pj.Error as e:
                print(f"Error setting up recorder: {str(e)}")

# Account callback
class AccountCallback(pj.AccountCallback):
    def __init__(self, account=None):
        super().__init__(account)

    def on_reg_state(self):
        print(f"Registration state: {self.account.info().reg_status} ({self.account.info().reg_reason})")

# Make a call
def make_call(lib, acc, number, domain="nyc.us.out.didww.com"):
    try:
        uri = f"sip:{number}@{domain}"
        print(f"Dialing: {uri}")
        call = acc.make_call(uri, cb=CallCallback())
        time.sleep(30)  # Wait for call to finish
        call.hangup()
        print(f"Call ended: {number}")
    except pj.Error as e:
        print(f"Error making call to {number}: {str(e)}")

# Main function
def main():
    global lib

    # Initialize the library
    lib = pj.Lib()

    try:
        # Configure the library
        media_cfg = pj.MediaConfig()
        media_cfg.no_vad = True
        media_cfg.enable_ice = False
        media_cfg.clock_rate = 16000  # Ensure compatibility with most systems
        
        # Initialize library
        lib.init(
            log_cfg=pj.LogConfig(level=3, callback=log_cb),
            media_cfg=media_cfg
        )

        # Use NULL sound device
        lib.set_null_snd_dev()
        print("Using NULL audio device")

        # Create UDP transport
        transport = lib.create_transport(pj.TransportType.UDP)
        print(f"Listening on {transport.info().host}:{transport.info().port}")

        # Start the library
        lib.start()

        # Configure SIP account
        acc_cfg = pj.AccountConfig()
        acc_cfg.id = f"sip:{os.getenv('SIP_USER')}@{os.getenv('SIP_DOMAIN')}"
        acc_cfg.reg_uri = f"sip:{os.getenv('SIP_DOMAIN')}"
        acc_cfg.auth_cred = [pj.AuthCred(
            os.getenv('SIP_AUTH_REALM'),
            os.getenv('SIP_AUTH_USERNAME'),
            os.getenv('SIP_AUTH_PASSWORD')
        )]
        
        # Create account
        acc = lib.create_account(acc_cfg, cb=AccountCallback())
        
        # Wait for registration to complete
        print("Waiting for registration...")
        time.sleep(3)

        # Phone numbers to call
        numbers = ["18889396675", "18555294494", "12064707000"]

        # Make calls sequentially
        for number in numbers:
            print(f"\nCalling {number}...")
            make_call(lib, acc, number)
            time.sleep(2)  # Small delay between calls

    except pj.Error as e:
        print(f"Exception: {str(e)}")
        sys.exit(1)

    finally:
        # Ensure library is properly destroyed
        if lib:
            print("Destroying library...")
            lib.destroy()
            lib = None

if __name__ == "__main__":
    main()
