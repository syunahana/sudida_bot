import time
import sys
import numpy as np
import cv2
import mss
import pyautogui
import easyocr
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging

# Setup logging
logging.basicConfig(
    filename='bot_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Detect whether we are running frozen (PyInstaller) or script
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = "."

# Configuration
URL = "https://sushida.net/play.html"
DEBUG_MODE = True # Show the captured window

def bot_loop(driver, reader):
    print("Bot loop started. Press 'q' in the debug window or Ctrl+C to stop.")
    
    with mss.mss() as sct:
        # Get the primary monitor
        monitor = sct.monitors[1]
        screen_width = monitor["width"]
        screen_height = monitor["height"]
        
        # Define a Region of Interest (ROI) for the text.
        # This is a rough guess for the center screen where text appears.
        # User might need to adjust this or we can implement auto-detection.
        # Sushida game window is usually centered.
        # Romaji text appears slightly above the center found "sushi".
        
        # Let's start with a box in the center.
        roi_width = 600
        roi_height = 150
        roi_left = (screen_width - roi_width) // 2
        roi_top = (screen_height // 2) - 50 # Slightly above center
        
        bbox = {
            "top": roi_top,
            "left": roi_left,
            "width": roi_width,
            "height": roi_height
        }
        
        last_text = ""
        frame_count = 0
        
        while True:
            t0 = time.time()
            frame_count += 1
            
            # Capture
            sct_img = sct.grab(bbox)
            frame = np.array(sct_img)
            # Remove alpha
            frame = frame[:, :, :3]
            # Convert BGRA to RGB/Gray for OCR? EasyOCR expects RGB or BGR.
            # mss gives BGRA. frame[:,:,:3] is BGR.
            
            # Preprocessing for better OCR?
            # Text is usually black/white on colored background.
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Thresholding might help
            # _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
            
            # Use easyocr
            # We only care about Romaji (english chars)
            try:
                results = reader.readtext(frame, allowlist='abcdefghijklmnopqrstuvwxyz-!?')
            except Exception as e:
                logging.error(f"OCR Error: {e}")
                continue
            
            detected_text = ""
            for (coords, text, conf) in results:
                if conf > 0.4: # low confidence threshold
                    detected_text += text + " "
            
            detected_text = detected_text.strip()
            
            if detected_text and detected_text != last_text:
                print(f"Detected: '{detected_text}'")
                
                # Filter out garbage (single chars that are likely noise?)
                if len(detected_text) > 1:
                    pyautogui.write(detected_text)
                    last_text = detected_text
            
            # Visualization
            if DEBUG_MODE:
                # Draw bbox on frame (not useful as frame IS the bbox)
                # Just show the frame
                display_frame = frame.copy()
                cv2.putText(display_frame, f"FPS: {1/(time.time()-t0):.1f}", (10, 20), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                cv2.imshow("Bot View", display_frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            # Save debug screenshot occasionally
            if frame_count % 50 == 0:
                 cv2.imwrite("latest_capture_debug.png", frame)
            
            # time.sleep(0.05)

def main():
    print("Initializing EasyOCR...")
    logging.info("Initializing EasyOCR...")
    try:
        reader = easyocr.Reader(['en'], gpu=False) # Changed to False for stability
        logging.info("OCR Initialized (GPU=False).")
    except Exception as e:
        print(f"Failed to init OCR: {e}")
        logging.exception("Failed to init OCR")
        return

    options = webdriver.ChromeOptions()
    # options.add_argument("--start-maximized")
    
    try:
        logging.info("Setting up ChromeDriver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logging.info("ChromeDriver started successfully.")
    except Exception as e:
        print(f"Failed to start Chrome: {e}")
        logging.exception("Failed to start Chrome")
        return
    
    try:
        driver.get(URL)
        print("Waiting for page load...")
        time.sleep(2)
        
        print("\n" + "="*40)
        print("INSTRUCTIONS:")
        print("1. Select the game mode (e.g. 3000 yen course).")
        print("2. Wait for the game countdown to finish.")
        print("3. Ensure the browser window is CENTERED on your main screen.")
        print("4. Press ENTER here to start the bot.")
        print("="*40 + "\n")
        
        input()
        
        # Give user time to switch focus back if needed
        print("Starting in 3 seconds...")
        time.sleep(3)
        
        bot_loop(driver, reader)

    except KeyboardInterrupt:
        print("Stopped by user.")
        logging.info("Stopped by user.")
    except Exception as e:
        print(f"Error: {e}")
        logging.exception("Fatal Error:")
    finally:
        logging.info("Closing driver and windows.")
        if 'driver' in locals():
            driver.quit()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
