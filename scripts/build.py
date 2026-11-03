import os
import sys
import argparse
import time

# Ensure scripts directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validate import validate_environment_and_data
from synthesize import synthesize_sentences
from render import render_timeline_and_video

def main():
    parser = argparse.ArgumentParser(description="Batch generate YouTube English Shadowing videos.")
    parser.add_argument("--input", default="data/daily_001.csv", help="Input CSV sentence file")
    parser.add_argument("--config", default="config.json", help="Configuration JSON file")
    parser.add_argument("--output", default="output/daily_001", help="Output directory")
    parser.add_argument("--work-dir", default=None, help="Intermediate working directory")
    parser.add_argument("--audio-only", action="store_true", help="Only synthesize audio files")
    parser.add_argument("--render-only", action="store_true", help="Skip audio synthesis and only render video")
    parser.add_argument("--from-id", type=str, default=None, help="Process sentences starting from this id")
    parser.add_argument("--to-id", type=str, default=None, help="Process sentences up to this id")
    parser.add_argument("--force", action="store_true", help="Force regenerate all audio and image caches")

    args = parser.parse_args()
    start_time = time.time()

    print("==================================================")
    print("  YouTube English Shadowing Video Generator")
    print("==================================================")
    print(f"Input CSV:  {args.input}")
    print(f"Config:     {args.config}")
    print(f"Output Dir: {args.output}")

    # Determine work directory
    if args.work_dir:
        work_dir = args.work_dir
    else:
        csv_basename = os.path.splitext(os.path.basename(args.input))[0]
        work_dir = os.path.join("work", csv_basename)
    print(f"Work Dir:   {work_dir}")

    # Step 1: Validation
    print("\n[Step 1/3] Validating configuration, system tools, and CSV data...")
    val_res = validate_environment_and_data(args.input, args.config)
    config = val_res["config"]
    rows = val_res["rows"]

    # Filter rows by --from-id and --to-id if specified
    if args.from_id or args.to_id:
        filtered = []
        started = False if args.from_id else True
        for r in rows:
            if not started and r["id"] == str(args.from_id):
                started = True
            if started:
                filtered.append(r)
                if args.to_id and r["id"] == str(args.to_id):
                    break
        rows = filtered
        print(f"Filtered sentence range: {len(rows)} sentences selected.")

    if not rows:
        print("Error: No sentences to process after filtering.")
        sys.exit(1)

    # Step 2: Audio Synthesis
    if not args.render_only:
        print(f"\n[Step 2/3] Synthesizing speech audio with Piper ({len(rows)} sentences)...")
        synthesized_items = synthesize_sentences(rows, config, work_dir, force=args.force)
    else:
        print("\n[Step 2/3] Skipping audio synthesis (--render-only specified). Loading existing audio metadata...")
        synthesized_items = []
        for r in rows:
            prefix = f"{int(r['id']):03d}" if r['id'].isdigit() else str(r['id'])
            norm_w = os.path.join(work_dir, f"{prefix}_normal.wav")
            slow_w = os.path.join(work_dir, f"{prefix}_slow.wav")
            if not os.path.exists(norm_w) or not os.path.exists(slow_w):
                raise FileNotFoundError(f"Missing cached audio for sentence {r['id']} in {work_dir}")
            
            # calculate durations
            import wave
            with wave.open(norm_w, "rb") as wf:
                dur_norm = wf.getnframes() / float(wf.getframerate())
            with wave.open(slow_w, "rb") as wf:
                dur_slow = wf.getnframes() / float(wf.getframerate())
                
            item = dict(r)
            item.update({
                "normal_wav": norm_w,
                "slow_wav": slow_w,
                "normal_duration": dur_norm,
                "slow_duration": dur_slow
            })
            synthesized_items.append(item)

    if args.audio_only:
        print("\n[Complete] Audio synthesis finished (--audio-only specified).")
        return

    # Step 3: Video Rendering and Assembly
    print(f"\n[Step 3/3] Rendering scene frames, timeline, and encoding final MP4...")
    result = render_timeline_and_video(synthesized_items, config, work_dir, args.output)

    elapsed = time.time() - start_time
    print("\n==================================================")
    print("  Generation Successfully Completed! ")
    print("==================================================")
    print(f"Total Sentences: {len(rows)}")
    print(f"Video Duration:  {result['total_duration']:.2f} seconds")
    print(f"MP4 Output:      {result['video_path']}")
    print(f"Timeline JSON:   {result['timeline_path']}")
    print(f"Elapsed Time:    {elapsed:.1f} seconds")

if __name__ == "__main__":
    main()
