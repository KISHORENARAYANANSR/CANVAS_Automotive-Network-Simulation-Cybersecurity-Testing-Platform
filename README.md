# 🚗 CANVAS  
### Automotive Network Simulation & Cybersecurity Testing Platform  

*Simulating the brain of a vehicle — in real time.*

---

## 📌 Overview

## CANVAS — Automotive Network Simulation & Cybersecurity Platform
*CAN-LIN Automotive Network Virtual Architecture Simulator*

An industry-grade automotive network simulation and cybersecurity testing platform designed to emulate real-world ECU communication, CAN/LIN networks, and in-vehicle cyber attacks.

---
## 🌐 Live Demo

https://canvas-platform.onrender.com/

---

## 🚀 Why This Matters

Modern vehicles rely on complex in-vehicle networks (CAN, LIN, Ethernet).  
Testing cybersecurity vulnerabilities and fault scenarios in real vehicles is expensive and risky.

CANVAS provides a safe environment to:
- Simulate ECU communication
- Test cyber attacks (Spoofing, DoS)
- Validate IDS systems
- Analyze real-time vehicle network behavior

---


## 📸 Screenshots  

### Dashboard View  
<img width="1919" height="1077" alt="image" src="https://github.com/user-attachments/assets/76ed2f2a-416b-4933-a37f-6aecdef30c69" />

### CAN Logger  
<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/7df27990-5f00-478d-bd7b-103dca6b07c5" />

### Fault Simulation  
<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/bfc35352-482b-4b7e-9320-07ca261eb0fa" />

### Vehicle Security (Cyber Attacks & IDS)  
<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/c16978d2-51bb-4c74-bc83-073b21740f1a" />

### System Report  
<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/3ba47c2f-3d92-44a8-89c8-fd383ccdc7e5" />

---

## 🎯 Key Features  

### 🚘 Real-Time Multi-ECU Simulation  
- Simulates multiple ECUs (Engine, ABS, Airbag, Transmission, BMS, Motor, Hybrid, Regen)  
- Real-time signal updates (Speed, RPM, Temperature, Torque, etc.)  
- Hybrid/EV drive mode visualization  

---

### 🔌 Automotive Network Protocols  
- CAN (Controller Area Network)  
- LIN (Local Interconnect Network)  
- Ethernet (Gateway simulation)  
- DBC-based message encoding/decoding using cantools  

---

### ⚙️ Deterministic Real-Time Scheduler  
- Single-threaded deterministic execution  
- High-precision timing using time.monotonic()  
- Maintains < 2ms jitter for consistent simulation  

---

### ⚠️ Fault Simulation (FMEA-Based)  
- Engine Overheat  
- Tyre Blowout / TPMS faults  
- ABS Failure  
- Battery Failure  
- Collision Event (Airbag Deployment)  

- Generates real DTC codes (e.g., P0217, C0750, B0001)  
- Updates system behavior dynamically  

---

### 🔐 Cybersecurity Testing  
- Speed Spoof Attack  
- Brake Spoof Attack  
- DoS Flood Attack  

- Simulates real CAN vulnerabilities  
- Injects malicious frames into the network  

---

### 🛡️ Intrusion Detection System (IDS)  
- Detects abnormal CAN traffic patterns  
- Identifies spoofed signals and anomalies  
- Logs attack details (target CAN ID, value changes)  
- Real-time alert visualization  

---

### 📊 Advanced Dashboard  
- Live vehicle telemetry  
- ECU status monitoring  
- CAN traffic analysis (messages/sec, bus load)  
- Fault & alert visualization  
- ADAS status indicators  

---

### 📄 AUTOSAR-Style Report Generation  
- ECU architecture overview  
- Signal flow mapping  
- Network communication structure  

---

## 🧠 System Architecture  

CANVAS models a realistic automotive architecture:

- ECUs communicate via CAN/LIN  
- Gateway ECU connects CAN, LIN, and Ethernet  
- DBC file defines signal structure and scaling  
- Scheduler ensures deterministic execution  
- Attack Simulator injects malicious frames  
- Secure Gateway (IDS) monitors and detects anomalies  

---

## 🛠️ Tech Stack  

- Backend: Python, Flask  
- Frontend: HTML, CSS, JavaScript  
- Communication: WebSockets  
- CAN Tools: cantools (DBC parsing and encoding)  
- Simulation Core: Custom deterministic scheduler  

---

## 🚀 How to Run  

### 1. Clone the repository  
git clone https://github.com/your-username/canvas.git

cd canvas

### 2. Install dependencies  
pip install -r requirements.txt

### 3. Run the application  
python app.py

### 4. Open in browser  
http://localhost:5000

---

## 🧪 Demo Flow  

1. **Normal Operation**  
   - Observe live ECU signals and vehicle state  

2. **Fault Simulation**  
   - Inject Engine Overheat or Tyre Blowout  
   - Observe DTC codes and system behavior  

3. **Cyber Attack Simulation**  
   - Trigger Speed Spoof or Brake Spoof  
   - Observe abnormal vehicle response  

4. **IDS Detection**  
   - View real-time alerts and intrusion logs  

---

## 💡 Use Cases  

- Automotive ECU network simulation  
- CAN bus cybersecurity research  
- Fault diagnostics and FMEA testing  
- Embedded systems learning  
- ADAS and vehicle system prototyping  

---

## 📈 Impact  

CANVAS provides a controlled environment to:
- Understand real vehicle communication systems  
- Test safety-critical faults without physical hardware  
- Analyze cybersecurity vulnerabilities in CAN networks  
- Demonstrate automotive system behavior in real time  

---

## 📌 Future Enhancements  

- ML-based anomaly detection  
- V2V communication integration  
- Hardware-in-the-loop (HIL) support  
- Cloud-based simulation and logging  
- Automotive protocol expansion (UDS, SOME/IP)  

---

## 👨‍💻 Author  

### **Kishore Narayanan S R**  
*IoT Engineering Student*  
Focused on Automotive Systems, Embedded AI, and Connected Mobility

---

## 📄 License
This project is licensed under the MIT License.
