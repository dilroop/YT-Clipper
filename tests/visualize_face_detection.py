#!/usr/bin/env python3
"""
Visualize face detection boundaries on a frame from test video
Outputs to tests/results/test-face-detection-viz/
"""

import sys
import cv2
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))


def create_test_output_folder():
    """Create timestamped output folder for test results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder = Path(__file__).parent / 'results' / f'test-face-detection-viz-{timestamp}'
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder


def write_verify_file(output_folder, image_path, face_count):
    """Generate VERIFY.txt with manual check instructions"""
    verify_text = f"""# Face Detection Visualization Test Results
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Output Files:
- {image_path.name}

## Detected: {face_count} face(s)

## What to Verify:

### Visual Elements:
1. **Red rectangles**: Face detection bounding boxes from OpenCV Haar Cascade
2. **Green rectangles**: Final 9:8 crop boxes used for reels
3. **Blue dots**: Face center points
4. **Labels**: Face dimensions and crop box sizes

### Check Points:
1. **Face detection accuracy**: Are real faces detected? Any false positives?
2. **Box coverage**: Does the green 9:8 box contain the full face with padding?
3. **Face positioning**: Is the face in the upper portion of the box?
4. **Top clearance**: Is there room above the head (no cut-off)?
5. **Ratio correctness**: Green box should be 9:8 ratio (1.125)

### For Dual-Face Videos:
- Both faces should have separate detection boxes
- Face size validation: Both faces within 50% size ratio
- If faces differ by >50% size, smaller one should be filtered out

### Common Issues to Check:
- **False positives**: Microphones, hands, or background objects detected as faces
- **Size mismatch**: One "face" much smaller than the other (should be filtered)
- **Cut-off tops**: Green box doesn't include top of head
- **Wrong ratio**: Green box not 9:8 (calculation error)

## Manual Verification Steps:
1. Open the image file
2. Examine red boxes (face detection)
3. Examine green boxes (crop regions)
4. Verify ratios and positioning
5. If test passes, delete this results folder
6. If test fails, keep folder and check reels_processor.py

## Debug Information:
- Input: tests/test_clip.mp4
- Frame captured: Frame 100 (~3-4 seconds in)
- Algorithm: Corner-based crop calculation
- Formula:
  * Box.LT-x = Face.LT-x - (face.width / 2)
  * Box.LT-y = Face.LT-y - (face.height / 4)
  * Box.RB-x = Face.RB-x + (face.width / 2)
  * Box.RB-y = Face.RB-y + (face.height * 0.35)
  * Then conform to 9:8 ratio
"""

    verify_path = output_folder / 'VERIFY.txt'
    verify_path.write_text(verify_text)
    print(f"\n📝 Generated verification instructions: {verify_path.name}")


def visualize_face_detection(video_path: Path, output_folder: Path, frame_number: int = 100):
    """
    Capture a frame and draw face detection boundaries

    Args:
        video_path: Path to video
        output_folder: Path to output folder
        frame_number: Which frame to capture
    """
    print(f"\n{'='*60}")
    print(f"Visualizing Face Detection")
    print(f"{'='*60}")

    # Load face detector
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)

    # Open video
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print(f"✗ Error: Cannot open video")
        return False, 0

    # Get video info
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"\nVideo info:")
    print(f"  Resolution: {width}x{height}")
    print(f"  Total frames: {total_frames}")
    print(f"  FPS: {fps:.2f}")

    # Seek to frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print(f"✗ Error: Cannot read frame {frame_number}")
        return False, 0

    timestamp = frame_number / fps
    print(f"\nCapturing frame {frame_number} (at {timestamp:.1f}s)")

    # Detect faces
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )

    print(f"\nDetected {len(faces)} face(s):")

    # Draw rectangles around faces and crop boxes
    for i, (x, y, w, h) in enumerate(faces):
        # Calculate face center
        center_x = x + w // 2
        center_y = y + h // 2

        print(f"\n  Face {i+1}:")
        print(f"    Position: ({x}, {y})")
        print(f"    Size: {w} x {h}")
        print(f"    Center: ({center_x}, {center_y})")
        print(f"    Coverage: {(w/width)*100:.1f}% width, {(h/height)*100:.1f}% height")

        # Calculate outer crop box (corner-based algorithm)
        face_lt_x = x
        face_lt_y = y
        face_rb_x = x + w
        face_rb_y = y + h

        box_lt_x = int(face_lt_x - w/2)
        box_lt_y = int(face_lt_y - (h / 4))
        box_rb_x = int(face_rb_x + w/2)
        box_rb_y = int(face_rb_y + (h * 0.35))
        box_width = box_rb_x - box_lt_x
        box_height = box_rb_y - box_lt_y

        print(f"\n    Crop Box (before 9:8 conforming):")
        print(f"      Size: {box_width}x{box_height}")
        print(f"      Ratio: {box_width/box_height:.3f}")

        # Conform to 9:8 ratio
        crop_width = box_width
        crop_height = int(crop_width * 8 / 9)

        if crop_height > crop_width:
            crop_width = int(crop_height * 9 / 8)

        # Re-center the crop box horizontally
        final_x = center_x - crop_width // 2
        final_y = box_lt_y

        print(f"\n    Final 9:8 Crop Box:")
        print(f"      Position: ({final_x}, {final_y})")
        print(f"      Size: {crop_width}x{crop_height}")
        print(f"      Ratio: {crop_width/crop_height:.3f} (should be 1.125)")

        # Draw red rectangle around face detection
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 5)

        # Draw green rectangle for the 9:8 crop box
        cv2.rectangle(frame, (final_x, final_y),
                     (final_x + crop_width, final_y + crop_height),
                     (0, 255, 0), 4)

        # Draw center point
        cv2.circle(frame, (center_x, center_y), 10, (255, 0, 0), -1)

        # Add labels
        face_label = f"Face {i+1}: {w}x{h}"
        box_label = f"9:8 Box: {crop_width}x{crop_height}"
        cv2.putText(frame, face_label, (x, y - 40), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 0, 255), 3)
        cv2.putText(frame, box_label, (final_x, final_y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 255, 0), 3)

    # Save image
    output_path = output_folder / 'face_detection_visualization.jpg'
    cv2.imwrite(str(output_path), frame)
    print(f"\n✓ Saved visualization to: {output_path.name}")

    return True, len(faces), output_path


def main():
    """Main function"""
    print("\n" + "="*60)
    print("FACE DETECTION VISUALIZATION TEST")
    print("="*60)

    # Find the test video
    test_video = Path(__file__).parent / 'test_clip.mp4'

    if not test_video.exists():
        print(f"\n✗ Error: Test video not found at {test_video}")
        return 1

    print(f"\n✓ Found test video: {test_video.name}")

    # Create output folder
    output_folder = create_test_output_folder()
    print(f"✓ Created output folder: {output_folder.name}")

    # Visualize at frame 100
    success, face_count, image_path = visualize_face_detection(test_video, output_folder, frame_number=100)

    if success:
        # Generate verification file
        write_verify_file(output_folder, image_path, face_count)

        print(f"\n{'='*60}")
        print("VISUALIZATION COMPLETE")
        print(f"{'='*60}")
        print(f"Output folder: {output_folder.name}")
        print(f"Faces detected: {face_count}")
        print(f"\n📋 Next steps:")
        print(f"   1. Review image in: {output_folder}")
        print(f"   2. Read VERIFY.txt for manual check instructions")
        print(f"   3. Delete folder if test passes")
        print(f"{'='*60}\n")

        # Open the image
        import subprocess
        subprocess.run(['open', str(image_path)])
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
