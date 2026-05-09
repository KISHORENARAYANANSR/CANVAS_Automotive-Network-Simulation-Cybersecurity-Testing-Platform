# 🚗 CANVAS  
### Automotive Network Simulation & Cybersecurity Testing Platform  

*Simulating the brain of a vehicle — in real time.*

---

## 📌 Overview

### CANVAS — Automotive Network Simulation & Cybersecurity Platform  
*CAN-LIN Automotive Network Virtual Architecture Simulator*

CANVAS is an industry-grade automotive network simulation and cybersecurity testing platform designed to emulate real-world ECU communication, CAN/LIN networks, and in-vehicle cyber attacks.

The platform simulates multiple automotive Electronic Control Units (ECUs), deterministic CAN communication, fault injection, IDS monitoring, and real-time dashboard visualization — all without requiring physical automotive hardware.

---

## 🌐 Live Demo

https://canvas-platform.onrender.com/

> ⚠️ Note: The platform is hosted on Render Free Tier.  
> Initial loading may take 30–60 seconds if the service is waking up.

---

## 🚀 Why This Matters

Modern vehicles rely heavily on in-vehicle communication networks such as:
- CAN Bus
- LIN Bus
- Automotive Ethernet

Testing cybersecurity vulnerabilities and fault scenarios on real vehicles is:
- Expensive
- Risky
- Hardware-dependent

CANVAS provides a safe and accessible environment to:
- Simulate ECU communication
- Test cyber attacks (Spoofing, DoS)
- Validate IDS systems
- Analyze real-time vehicle network behavior
- Perform FMEA-based automotive testing

---

## ▶️ Simulation Lifecycle Control

CANVAS uses a controlled simulation lifecycle system similar to professional automotive simulators.

### Features
- START SIMULATION
- STOP SIMULATION
- Idle resource optimization
- Dynamic ECU boot sequence
- Real-time CAN traffic activation
- Live telemetry synchronization

The dashboard loads in an OFFLINE state initially and activates only when the user starts the simulation.

---

## 📸 Screenshots  

### Dashboard View  
<img width="1918" height="1078" alt="image" src="https://github.com/user-attachments/assets/e43bd31b-fdeb-41fa-9cb4-ff754724839e" />

### CAN Logger  
<img width="1917" height="1078" alt="image" src="https://github.com/user-attachments/assets/5743a427-1e09-489d-942b-90c9291d83d7" />

### Fault Simulation  
<img width="1917" height="1078" alt="image" src="https://github.com/user-attachments/assets/fe5e81a8-906b-4b5f-a95c-16dc5ab7b75f" />

### Vehicle Security (Cyber Attacks & IDS)  
<img width="1918" height="1077" alt="image" src="https://github.com/user-attachments/assets/15b79a83-d505-4835-a8d1-f04f0b9865ff" />

### System Report  
<img width="1918" height="1077" alt="image" src="https://github.com/user-attachments/assets/9fa00e57-28b8-4813-b7f1-9f887dd9ea0c" />

---

## 🎯 Key Features  

### 🚘 Real-Time Multi-ECU Simulation  
- Simulates multiple ECUs:
  - Engine
  - ABS
  - Airbag
  - Transmission
  - BMS
  - Motor
  - Hybrid Control
  - Regenerative Braking

- Real-time signal updates:
  - Speed
  - RPM
  - Temperature
  - Torque
  - Battery SOC
  - Brake Pressure

---

### 🔌 Automotive Network Protocols  
- CAN (Controller Area Network)
- LIN (Local Interconnect Network)
- Automotive Ethernet
- DBC-based message encoding/decoding using cantools

---

### ⚙️ Deterministic Real-Time Scheduler  
- High-precision execution
- `time.monotonic()` based scheduling
- < 2ms timing jitter
- Stable ECU cycle synchronization

---

### ⚠️ Fault Simulation (FMEA-Based)  
Supports:
- Engine Overheat
- Tyre Blowout
- ABS Failure
- Battery Failure
- Collision Event

Generates:
- Real OBD-II DTC codes
- Dynamic vehicle behavior changes
- ADAS responses

---

### 🔐 Cybersecurity Testing  
Supported attacks:
- Speed Spoof Attack
- Brake Spoof Attack
- DoS Flood Attack

Capabilities:
- CAN frame injection
- Message manipulation
- Traffic flooding simulation

---

### 🛡️ Intrusion Detection System (IDS)  
- Detects abnormal CAN traffic
- Detects spoofed signal anomalies
- Real-time security alerts
- Attack event tracking and logging

---

### 📊 Advanced Dashboard  
Includes:
- Live telemetry gauges
- ECU monitoring
- CAN traffic analytics
- Bus load visualization
- DTC visualization
- IDS alert visualization
- ADAS indicators

---

### 📄 AUTOSAR-Style Report Generation  
- ECU architecture mapping
- Signal flow overview
- Communication structure reporting
- Diagnostic summaries

---

## 🧠 System Architecture  

CANVAS models a realistic automotive communication architecture:

- Multi-ECU communication over CAN/LIN
- Gateway ECU bridging CAN, LIN, and Ethernet
- DBC-driven signal encoding/decoding
- Deterministic scheduler execution
- IDS-enabled secure gateway monitoring
- Cyber attack simulation layer

---

## ☁️ Cloud Deployment

The platform is publicly deployed using Render Cloud Platform.

### Deployment Features
- Public cloud hosting
- Real-time Socket.IO communication
- Simulation lifecycle control
- Automatic GitHub redeployment
- Free-tier optimized architecture

---

## 🛠️ Tech Stack  

### Backend
- Python
- Flask
- Flask-SocketIO

### Frontend
- HTML
- CSS
- JavaScript

### Communication
- WebSockets

### CAN Tools
- cantools
- python-can

### Hosting
- Render Cloud Platform

---

## 🚀 Local Installation  

### 1. Clone Repository

```bash
git clone https://github.com/KISHORENARAYANANSR/CANVAS_Automotive-Network-Simulation-Cybersecurity-Testing-Platform.git

cd CANVAS_Automotive-Network-Simulation-Cybersecurity-Testing-Platform
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Application

```bash
python run.py
```

### 4. Open Browser

```bash
http://localhost:5000
```

---

## 🧪 Demo Flow  

### 1. Normal Operation
- Observe live ECU telemetry
- Monitor CAN traffic
- View bus load and ECU activity

### 2. Fault Injection
- Trigger Engine Overheat
- Trigger Tyre Blowout
- Observe DTC generation and ADAS response

### 3. Cybersecurity Testing
- Launch Speed Spoof Attack
- Launch Brake Spoof Attack
- Launch DoS Attack

### 4. IDS Detection
- Observe real-time attack alerts
- Analyze abnormal traffic detection

---

## 💡 Use Cases  

- Automotive ECU network simulation
- CAN bus cybersecurity research
- FMEA validation
- Embedded systems education
- Automotive software prototyping
- IDS testing and validation

---

## 📈 Impact  

CANVAS enables:
- Safe testing of vehicle network vulnerabilities
- Real-time automotive system visualization
- Hardware-independent automotive experimentation
- Accessible automotive cybersecurity research
- Advanced educational automotive simulation

---

## 📌 Future Enhancements  

- ML-based anomaly detection
- V2V communication integration
- Hardware-in-the-loop (HIL) support
- Cloud simulation orchestration
- UDS / SOME-IP support
- Automotive digital twin concepts

---

## 👨‍💻 Author  

### **Kishore Narayanan S R**  
*IoT Engineering Student*  
Focused on Automotive Systems, Embedded AI, and Connected Mobility

---

## 📄 License

This project is licensed under the MIT License.
