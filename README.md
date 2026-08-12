Camera Sync Checker is a desktop utility app built with Python and PyQt designed to streamline and verify camera synchronization across multiple blender scenes/files.

## 🚀 Features
* **Intuitive GUI:** Clean, responsive user interface built with PyQt.
* **Persistent Caching:** Safely saves user configurations and cache data directly to the local AppData directory following Windows best practices.
* **Data Storing:** Stores extracted data as an accessible '.csv' file to be read anytime by the app.
* **Blender Integration:** Bundles custom extraction and fixing scripts (`blender_extractor.py` and `blender_fixer.py`) to process 3D pipeline data seamlessly.
* **Custom Assets:** Styled with custom window branding and UI icons.

---

## 🛠️ Built With
* **Python** 
* **PyQt** (Graphical User Interface)
* **PyInstaller** (Executable compilation)
* **Pathlib** (Modern file system path handling)

---

## 📦 Installation & Usage

### Option 1: Run the Pre-compiled App (Recommended for Users)

1. Head over to the **[Releases](../../releases)** page of this repository.
2. Download the latest `CameraChecker.zip` archive.
3. Extract the contents anywhere on your computer.
4. Double-click `CameraChecker.exe` to run the application.
5. If not set already, locate your `Blender.exe` installation for the app to run smoothly.

### Option 2: Run from Source (For Developers)
If you want to run or modify the code locally:

1. Clone the repository: \
git clone https://github.com/Newsuprano/camera_checker.git \
cd camera_checker \
3. Create and activate a virtual environment: \
python -m venv .venv \
.venv\Scripts\Activate.ps1  # On Windows PowerShell \
5. Install dependencies: \
pip install -r requirements.txt \
7. Run the main application: \
python src/main.py \

---

## 📬 Contact

* GitHub: [@Newsuprano](https://github.com/Newsuprano)
* Email : newsuprano.yt@gmail.com
