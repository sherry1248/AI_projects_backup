import os
import csv
import cv2
from pyzbar.pyzbar import decode
import lcddriver
import serial
import RPi.GPIO as GPIO
import time
import tkinter as tk
from tkinter import simpledialog

# Initialize serial communication
port = serial.Serial("/dev/ttyS0", 9600, timeout=0.1)

# Camera setup
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# LCD setup
display = lcddriver.lcd()

# GPIO setup
IR_SENSORS = [21, 20, 16, 12]
GPIO.setmode(GPIO.BCM)
for sensor in IR_SENSORS:
    GPIO.setup(sensor, GPIO.IN)

# File and slot setup
csv_file = 'inventory.csv'
slot_status = {idx: False for idx in range(len(IR_SENSORS))}  # Tracks slot occupancy status
last_action_time = {idx: 0 for idx in range(len(IR_SENSORS))}  # Tracks the last action time for each slot
timeout_duration = 15  # Grace period in seconds for IR sensor checks after an action


def send_sms(phone_number, message):
    port.write(b'AT\r')
    time.sleep(1)
    print(port.readline().decode())  # Read and print response

    port.write(b'AT+CMGF=1\r')  # Set SMS mode to text
    time.sleep(1)
    print(port.readline().decode())  # Read and print response

    port.write(f'AT+CMGS="{phone_number}"\r'.encode())  # Set recipient number
    time.sleep(1)
    print(port.readline().decode())  # Read and print response

    port.write(message.encode() + b"\x1A")  # Send message & end with Ctrl+Z
    time.sleep(3)
    print(port.read_all().decode())  # Read the final response

    print("SMS Sent Attempted!")




# Check if the CSV file exists, and initialize accordingly
if os.path.exists(csv_file):
    print(f"File '{csv_file}' exists. Reading existing data...")
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)  # Load all rows into a list
    valid_rows = []  # List to store valid rows (where the item is detected)
    for row in rows:
        # Parse row and slot from the file
        row_num = int(row['Row'].split()[1])  # Extract row number (e.g., "Row 1")
        slot_num = int(row['Slot'])  # Extract slot number
        slot_idx = (row_num - 1) * 2 + (slot_num - 1)  # Calculate slot index
        if not GPIO.input(IR_SENSORS[slot_idx]):  # IR sensor detects an object (active low)
            slot_status[slot_idx] = True  # Mark the slot as occupied
            valid_rows.append(row)  # Keep this row
        else:
            print(f"Slot {slot_num} in Row {row_num} is empty. Removing item from CSV.")

    # Write back only the valid rows to the CSV file
    with open(csv_file, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=["Date Time", "Row", "Slot", "Item", "Expiry"])
        writer.writeheader()  # Re-add header
        writer.writerows(valid_rows)  # Write only valid rows
else:
    print(f"File '{csv_file}' does not exist. Creating a new file...")
    with open(csv_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["Date Time", "Row", "Slot", "Item", "Expiry"])

# GUI setup
root = tk.Tk()
root.withdraw()

selected_row = None

def choose_slot():
    global selected_row
    slot = simpledialog.askstring("Slot Selection", f"Select slot for Row {selected_row}")
    return slot

# Define product details based on barcode
product_details = {
    '1234567890487': {"name": "Santoor", "expiry": "2026-12-31"},
    '2345689589568': {"name": "Closeup", "expiry": "2026-06-15"},
    '9876543270726': {"name": "Ponds ",  "expiry": "2026-11-20"},
    '4325675679938': {"name": "Nivea ",  "expiry": "2027-12-21"}
}
count=0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    rcv = port.readline().strip()
    #print(rcv)
    if(len(rcv)):
        count+=1
    # RFID row selection logic
    if rcv == b'4F0070A90593':  # RFID for Row 1
        selected_row = 1
        row_slots = [(selected_row - 1) * 2, (selected_row - 1) * 2 + 1]
        if all(slot_status[idx] for idx in row_slots):  # Check if both slots in Row 1 are occupied
            print("Row 1 is full. Cannot add more products.")
            display.lcd_clear()
            display.lcd_display_string("Row 1 Full", 1)
            time.sleep(2)
            selected_row = None  # Clear the selection since the row is full
        else:
            display.lcd_clear()
            display.lcd_display_string("Row 1 selected", 1)
            time.sleep(2)
        if(count>1):
            print("sending sms")
            send_sms("+917993927229", "Added Products to Rack1")
            send_sms("+917816079601", "Added Products to Rack1")
        
    elif rcv == b'4F007C8F41FD':  # RFID for Row 2
        selected_row = 2
        row_slots = [(selected_row - 1) * 2, (selected_row - 1) * 2 + 1]
        if all(slot_status[idx] for idx in row_slots):  # Check if both slots in Row 2 are occupied
            print("Row 2 is full. Cannot add more products.")
            display.lcd_clear()
            display.lcd_display_string("Row 2 Full", 1)
            time.sleep(2)
            selected_row = None  # Clear the selection since the row is full
        else:
            display.lcd_clear()
            display.lcd_display_string("Row 2 selected", 1)
            time.sleep(2)
        if(count>1):
            send_sms("+917993927229", "Added Products to Rack2")
            send_sms("+919666176433", "Added Products to Rack2")
        
    # Process barcodes
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    barcodes = decode(gray)

    for barcode in barcodes:
        barcode_data = barcode.data.decode('utf-8')
        barcode_type = barcode.type
        print(f"Detected: {barcode_data} (Type: {barcode_type})")

        if barcode_data in product_details:
            product = product_details[barcode_data]
            product_name = product["name"]
            product_expiry = product["expiry"]
            print(f"Product: {product_name}, Expiry: {product_expiry}")

            if selected_row:
                # Check if both slots in the selected row are already occupied
                if all(slot_status[idx] for idx in row_slots):
                    print(f"Row {selected_row} is full. Cannot add more products.")
                    display.lcd_clear()
                    display.lcd_display_string(f"Row {selected_row} Full", 1)
                    time.sleep(2)
                    continue

                slot = choose_slot()
                if slot:
                    slot_idx = (selected_row - 1) * 2 + (int(slot) - 1)
                    if slot_status[slot_idx]:  # Check if the slot is already occupied
                        print(f"Slot {slot} in Row {selected_row} is already occupied. Cannot add product.")
                        display.lcd_clear()
                        display.lcd_display_string("Slot Occupied", 1)
                        display.lcd_display_string(f"Row {selected_row}, Slot {slot}", 2)
                        time.sleep(2)
                    else:
                        with open(csv_file, 'a') as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                time.strftime("%Y-%m-%d %H:%M:%S"),
                                f"Row {selected_row}",
                                slot,
                                product_name,
                                product_expiry
                            ])
                        slot_status[slot_idx] = True  # Mark slot as occupied
                        last_action_time[slot_idx] = time.time()  # Record the time of action
                        display.lcd_clear()
                        display.lcd_display_string(f"{product_name} added", 1)
                        display.lcd_display_string(f"Row {selected_row}, Slot {slot}", 2)
                        time.sleep(1)
        else:
            print(f"Unknown barcode: {barcode_data}")
            display.lcd_clear()
            display.lcd_display_string("Unknown Product", 1)
            time.sleep(1)

        for i in range(20):
            ret, frame = cap.read()


    # Runtime IR sensor logic to remove items with grace time
    current_time = time.time()
    for idx, sensor in enumerate(IR_SENSORS):
        row = (idx // 2) + 1
        slot = (idx % 2) + 1
        # Only check IR sensors after the grace time has elapsed
        if current_time - last_action_time[idx] > timeout_duration:
            if GPIO.input(sensor):  # No item detected (IR is inactive)
                if slot_status[idx]:  # Only process if slot was previously occupied
                    print(f"No product detected in Slot {slot}, Row {row}. Removing entry from CSV.")
                    with open(csv_file, 'r') as f:
                        rows = list(csv.reader(f))
                    with open(csv_file, 'w') as f:
                        writer = csv.writer(f)
                        #writer.writerow(["Date Time", "Row", "Slot", "Item", "Expiry"])  # Write header again
                        for row_data in rows:
                            if not (row_data[1] == f"Row {row}" and row_data[2] == str(slot)):
                                writer.writerow(row_data)
                    slot_status[idx] = False  # Mark slot as unoccupied
                    display.lcd_clear()
                    display.lcd_display_string("Item removed", 1)
                    display.lcd_display_string(f"Row {row}, Slot {slot}", 2)
                    time.sleep(2)


    cv2.imshow("Barcode Scanner", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
    
