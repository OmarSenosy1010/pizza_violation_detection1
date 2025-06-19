"""
roi_selector.py
Allows the user to select Regions of Interest (ROIs) from the first frame of a video and saves them to config.json.
"""
import cv2
import json

class ROI:
    """
    ROI selector class for interactive selection of multiple ROIs from a video frame.
    """
    def __init__(self, frame):
        self.frame = frame

    def pound_inters(self):
        """
        Opens an OpenCV window for the user to select multiple ROIs.
        Returns a list of ROI tuples.
        """
        if self.frame is None:
            print("No frame provided.")
            return []

        rois = cv2.selectROIs("Select Multiple ROIs", self.frame, showCrosshair=True)
        cv2.destroyWindow("Select Multiple ROIs")

        roi_list = [tuple(map(int, roi)) for roi in rois]
        print("Selected ROIs:")
        for i, roi in enumerate(roi_list):
            print(f"ROI {i+1}: {roi}")

        return roi_list

def main():
    """
    Reads the first frame from the video, allows the user to select ROIs, and saves them to config.json.
    """
    video_path = "videos\Sah_w_b3dha_ghalt.mp4"  
    config_path = "config.json"

    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 100)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("❌ Failed to read frame from video.")
        return

    roi_selector = ROI(frame)
    roi_list = roi_selector.pound_inters()

    if roi_list:
        with open(config_path, "w") as f:
            json.dump({"rois": roi_list}, f, indent=2)
        print(f"✅ Saved {len(roi_list)} ROIs to {config_path}")

if __name__ == "__main__":
    main()
