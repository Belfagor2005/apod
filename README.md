<h1 align="center">🌌 APOD – Astronomy Picture of the Day</h1>

![Visitors](https://komarev.com/ghpvc/?username=Belfagor2005&label=Repository%20Views&color=blueviolet)
![Version](https://img.shields.io/badge/version-2.1-blue)
[![Enigma2](https://img.shields.io/badge/Enigma2-Plugin-ff6600.svg)](https://www.enigma2.net)
![Python](https://img.shields.io/badge/Python3-only-orange.svg)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python package](https://github.com/Belfagor2005/apod/actions/workflows/pylint.yml/badge.svg)](https://github.com/Belfagor2005/apod/actions/workflows/pylint.yml)
[![Donate](https://img.shields.io/badge/_-Donate-red.svg?logo=githubsponsors&labelColor=555555&style=for-the-badge)](Maintainers.md#maintainers "Donate")

<p align="center">
  <img src="https://github.com/Belfagor2005/apod/blob/main/usr/lib/enigma2/python/Plugins/Extensions/apod/logo.png" height="120">
</p>

---

**Enigma2 project**

**APOD Plugin E2** – displays **NASA Astronomy Picture of the Day**.
Supports daily images from NASA: [APOD](https://apod.nasa.gov/)


---

### **How to Use the NASA API Key for the APOD Plugin** 🚀
#### **1. Obtain the NASA API Key** 🌌
To access the Astronomy Picture of the Day (APOD) data from NASA, you need a valid API key.

* Visit the NASA API registration page:
  `https://api.nasa.gov/`

* After completing the registration, you will receive a unique API key that grants access to the data.
---

#### **2. Adding the API Key to Your System** 🔑
Once you have the API key, store it securely on your system.

##### **Method 1: Create a file for the API Key** 📂
Run this command in your terminal to create the file:

```bash
echo "YOUR_NASA_API_KEY" > /etc/apod_api_key
```

Set proper permissions so only the owner can read/write:

```bash
chmod 600 /etc/apod_api_key
```

Make sure the file is accessible and secure.

---

#### **3. Restart the System to Apply Changes** 🔄
After saving the API key, restart the plugin or GUI so the key can be loaded correctly.

---

#### **4. Troubleshooting** ⚠️
* **Invalid API Key Error**: Check the contents of your key file and ensure the key is copied exactly as provided.
* **Permission Issues**: Ensure the key file has the correct permissions (`chmod 600`).
* **Missing File**: Make sure the key exists in one of the expected paths.
---
Once done, the plugin should be able to access NASA's APOD data and display the Astronomy Picture of the Day properly. ✨
---
