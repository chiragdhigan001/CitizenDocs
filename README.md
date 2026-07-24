# CitizenDocs 🏛️🔒

**Zero uploads. Absolute privacy. For strict forms and sensitive data.**

ILoveGovernmentWebsites is a serverless, localhost-first media processing suite designed to handle the strict file-size limits, specific format requirements, and precise aspect ratios demanded by government portals and academic applications. 

By running entirely on your local machine, it guarantees that your sensitive documents, IDs, and passport photos are never uploaded to a third-party server.

## 🚀 Features

*   **Targeted KB Reducer:** Employs a custom binary-search compression algorithm to mathematically pinpoint the maximum possible image quality that fits exactly beneath your target file size (e.g., strictly < 200KB).
*   **Visual Crop Editor:** Integrated `Cropper.js` interface for precise manual cropping (Passport 1:1, Document 4:5, Landscape 16:9, or Free Size).
*   **Universal Format Converter:** Instantly transcode between PNG, JPG, WebP, AVIF, HEIC, GIF, BMP, and ICO. 
*   **Media Extraction:** Lightning-fast MP4 to MP3 audio extraction.
*   **Image to PDF Composer:** A visual staging area to drag, drop, reorder, and compile multiple images into a single PDF document.
*   **Session History:** 24-hour local tracking of processed files with inline renaming, batch merging, and one-click downloads.

## 🛠️ Tech Stack

*   **Backend:** Python 3, FastAPI, Pillow (with AVIF/HEIC plugins), MoviePy, Asyncio
*   **Frontend:** HTML5, Tailwind CSS (Liquid Glassmorphism UI), Cropper.js
*   **Architecture:** Asynchronous routing with CPU-bound image processing safely offloaded to separate background threads.

## 📦 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/DevAyu-Codes/ILoveGovernmentWebsites.git
   cd ILoveGovernmentWebsites
   ```
2. **Install the required Python dependencies:**
    
    It is recommended to use a virtual environment.
    ```bash
    pip install -r requirements.txt
    ```
3. **Start the local server:**
    ```bash
    uvicorn main:app --reload
    ```
4. **Access the application:**

    Open your browser and navigate to `http://127.0.0.1:8000`.

## 💡 How It Works (The Compression Engine)

Unlike standard image compressors that step down quality linearly (which is incredibly slow and often overshoots target sizes), this tool uses a Binary Search Algorithm. It tests the exact midpoint of quality and scale factors, eliminating half the search space with every iteration. This allows it to find the absolute highest resolution that fits your exact byte limit in 7 steps or less, ensuring maximum clarity for critical documents.

## 👨‍💻 Author

[Chirag](https://github.com/chiragdhigan001/)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
