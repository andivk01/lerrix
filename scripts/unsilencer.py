print("Removed implementation, currently not working in this version")
# from lib.unsilence.Silencer import Silencer
# import os
# import argparse
# import json
# from lib.scrape.Video import Video

# codecs_available = ["copy", "libx265", "libx264", "h264_amf"]
# log_directory = "logs"
# silence_history = os.path.join(log_directory, "silence_history.log")

# parser = argparse.ArgumentParser(description='LERRIX v0.1')
# group = parser.add_mutually_exclusive_group()
# parser.add_argument('-id', '--in-dir', help='Unsilence videos from the directory')
# parser.add_argument('-history', '--history-file', help='History file, used to avoid unsilencing already unsilenced videos', default=silence_history)
# parser.add_argument('-od', '--out-dir', help='Unsilence videos from to the directory')
# parser.add_argument('-c', "--codec", help="Video codec for unsilencer's output", choices=codecs_available, default="libx265")
# args = parser.parse_args()

# if args.in_dir is None:
#     print("Please specify the input directory")
#     exit(1)
# else:
#     in_dirs = [args.in_dir]
#     out_dirs = [args.out_dir]
#     if args.in_dir[0] == "[": # it's a json array
#         in_dirs = json.loads(args.in_dir)
#     if args.out_dir[0] == "[": # it's a json array
#         out_dirs = json.loads(args.in_dir)
#     if len(in_dirs) != len(out_dirs):
#         print("Please specify the same number of input and output directories")
#         exit(1)
#     for idx, in_dir in enumerate(in_dirs):
#         videos = []
#         for file in os.listdir(in_dir):
#             videos.append(Video(file, os.path.join(in_dir, file), file)),
#         silencer = Silencer(args.history_file)
#         silencer.unsilence_videos(videos, out_dirs[idx], codec=args.codec)