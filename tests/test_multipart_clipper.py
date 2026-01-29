#!/usr/bin/env python3
"""
Test Multipart Clip Generation
Tests the fixed multipart clip stitching functionality
"""

import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.clipper import VideoClipper


def get_video_duration(video_path):
    """Get video duration using ffprobe"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def test_multipart_clip_basic():
    """Test basic 3-part multipart clip creation"""
    print("\n" + "="*80)
    print("TEST 1: Basic Multi-Part Clip (3 parts)")
    print("="*80)

    # Setup
    test_dir = Path(__file__).parent
    results_dir = test_dir / "results"
    results_dir.mkdir(exist_ok=True)

    video_path = test_dir / "test_clip3.mp4"
    output_path = results_dir / "output_test_multipart_basic.mp4"

    if not video_path.exists():
        print(f"❌ SKIP: Test video not found at {video_path}")
        return False

    clipper = VideoClipper()

    # Test data: 3 parts from different timestamps
    parts = [
        {'start': 62, 'end': 78, 'duration': 16},
        {'start': 216, 'end': 230, 'duration': 14},
        {'start': 257, 'end': 282, 'duration': 25}
    ]

    print(f"\n📹 Source video: {video_path.name}")
    print(f"📦 Parts to stitch:")
    for i, part in enumerate(parts, 1):
        print(f"   Part {i}: {part['start']}s - {part['end']}s ({part['duration']}s)")

    # Calculate expected duration
    expected_duration = sum(p['duration'] for p in parts) - 0.1 * (len(parts) - 1)
    print(f"\n⏱️  Expected duration: {expected_duration:.1f}s (with 0.1s crossfade)")

    # Create multipart clip
    print(f"\n🎬 Creating multipart clip...")
    result = clipper.create_multipart_clip(
        video_path=str(video_path),
        parts=parts,
        output_path=str(output_path)
    )

    # Validate result
    if not result['success']:
        print(f"\n❌ FAILED: Clip creation failed")
        print(f"   Error: {result['error']}")
        return False

    print(f"\n✅ Clip created: {output_path.name}")

    # Check file exists
    if not output_path.exists():
        print(f"❌ FAILED: Output file not created")
        return False

    # Check duration
    actual_duration = get_video_duration(output_path)
    print(f"\n📊 Duration check:")
    print(f"   Expected: {expected_duration:.1f}s")
    print(f"   Actual:   {actual_duration:.1f}s")

    diff = abs(actual_duration - expected_duration)
    print(f"   Diff:     {diff:.1f}s")

    if diff < 1.0:
        print(f"\n✅ TEST PASSED: Duration is correct!")
        return True
    else:
        print(f"\n❌ FAILED: Duration mismatch (expected ~{expected_duration:.1f}s, got {actual_duration:.1f}s)")
        return False


def test_multipart_clip_2parts():
    """Test 2-part multipart clip"""
    print("\n" + "="*80)
    print("TEST 2: Two-Part Clip")
    print("="*80)

    test_dir = Path(__file__).parent
    results_dir = test_dir / "results"
    results_dir.mkdir(exist_ok=True)

    video_path = test_dir / "test_clip3.mp4"
    output_path = results_dir / "output_test_multipart_2parts.mp4"

    if not video_path.exists():
        print(f"❌ SKIP: Test video not found")
        return False

    clipper = VideoClipper()

    # Test with 2 parts
    parts = [
        {'start': 10, 'end': 25, 'duration': 15},
        {'start': 100, 'end': 120, 'duration': 20}
    ]

    print(f"\n📦 Parts: {parts[0]['start']}-{parts[0]['end']}s, {parts[1]['start']}-{parts[1]['end']}s")

    expected_duration = sum(p['duration'] for p in parts) - 0.1
    print(f"⏱️  Expected: {expected_duration:.1f}s")

    result = clipper.create_multipart_clip(
        video_path=str(video_path),
        parts=parts,
        output_path=str(output_path)
    )

    if not result['success']:
        print(f"❌ FAILED: {result['error']}")
        return False

    actual_duration = get_video_duration(output_path)
    diff = abs(actual_duration - expected_duration)

    print(f"📊 Duration: {actual_duration:.1f}s (diff: {diff:.1f}s)")

    if diff < 1.0:
        print(f"✅ TEST PASSED")
        return True
    else:
        print(f"❌ FAILED: Duration mismatch")
        return False


def test_multipart_clip_single_part():
    """Test single-part clip (should use regular create_clip)"""
    print("\n" + "="*80)
    print("TEST 3: Single-Part Clip (Fallback Test)")
    print("="*80)

    test_dir = Path(__file__).parent
    results_dir = test_dir / "results"
    results_dir.mkdir(exist_ok=True)

    video_path = test_dir / "test_clip3.mp4"
    output_path = results_dir / "output_test_multipart_singlepart.mp4"

    if not video_path.exists():
        print(f"❌ SKIP: Test video not found")
        return False

    clipper = VideoClipper()

    # Single part - should fall back to create_clip
    parts = [
        {'start': 50, 'end': 70, 'duration': 20}
    ]

    print(f"\n📦 Single part: {parts[0]['start']}-{parts[0]['end']}s")

    expected_duration = 20.0
    print(f"⏱️  Expected: {expected_duration:.1f}s")

    result = clipper.create_multipart_clip(
        video_path=str(video_path),
        parts=parts,
        output_path=str(output_path)
    )

    if not result['success']:
        print(f"❌ FAILED: {result['error']}")
        return False

    actual_duration = get_video_duration(output_path)
    diff = abs(actual_duration - expected_duration)

    print(f"📊 Duration: {actual_duration:.1f}s (diff: {diff:.1f}s)")

    if diff < 1.0:
        print(f"✅ TEST PASSED")
        return True
    else:
        print(f"❌ FAILED: Duration mismatch")
        return False


def test_existing_clip():
    """Verify existing test_clip3.mp4 (full source video)"""
    print("\n" + "="*80)
    print("TEST 4: Verify Existing test_clip3.mp4 (Full Video)")
    print("="*80)

    clip_path = Path(__file__).parent / "test_clip3.mp4"

    if not clip_path.exists():
        print(f"❌ SKIP: test_clip3.mp4 not found")
        return False

    duration = get_video_duration(clip_path)
    file_size = clip_path.stat().st_size / (1024 * 1024)  # MB

    print(f"\n📹 File: {clip_path.name}")
    print(f"📊 Duration: {duration:.1f}s ({duration/60:.1f} minutes)")
    print(f"💾 Size: {file_size:.1f} MB")

    # Expected to be the full source video (~890 seconds / ~15 minutes)
    if 880 <= duration <= 900:
        print(f"✅ TEST PASSED: Duration is in expected range for full video (880-900s)")
        return True
    else:
        print(f"❌ FAILED: Duration {duration:.1f}s is outside expected range (880-900s)")
        print(f"   Expected: Full source video (~15 minutes)")
        return False


def cleanup_test_outputs():
    """Clean up test output files"""
    print("\n" + "="*80)
    print("Cleaning up test outputs...")
    print("="*80)

    test_dir = Path(__file__).parent
    results_dir = test_dir / "results"

    if not results_dir.exists():
        print("No results directory to clean up")
        return

    output_files = list(results_dir.glob("output_test_*.mp4"))

    if not output_files:
        print("No test output files to clean up")
        return

    for file in output_files:
        try:
            file.unlink()
            print(f"🗑️  Removed: {file.name}")
        except Exception as e:
            print(f"⚠️  Could not remove {file.name}: {e}")


def main():
    """Run all tests"""
    print("\n" + "🎬" * 40)
    print("MULTIPART CLIP GENERATION TEST SUITE")
    print("🎬" * 40)

    tests = [
        ("Basic 3-Part Clip", test_multipart_clip_basic),
        ("Two-Part Clip", test_multipart_clip_2parts),
        ("Single-Part Fallback", test_multipart_clip_single_part),
        ("Verify test_clip3.mp4", test_existing_clip),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n❌ EXCEPTION in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    # Cleanup (disabled to keep results for inspection)
    # cleanup_test_outputs()

    print("\n" + "="*80)
    print(f"📁 Test outputs saved to: {Path(__file__).parent / 'results'}")
    print("="*80)
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
