import sys
import math
import ffmpeg
from os import path
from faster_whisper import WhisperModel

if len(sys.argv) < 2:
    print("Expected path to the video file")
    exit(1)

input_video = sys.argv[1]
lang = None
isForced = False
if len(sys.argv) >= 3 and len(sys.argv[2]) == 2:
    lang = sys.argv[2]
if len(sys.argv) >= 4 and "--force" in sys.argv:
    isForced = True


video_directory = path.dirname(input_video)
print("Parsed information")
print("=======================")
print("Video:")
print(input_video)
if (lang is not None):
    print("Language:", lang)
print("=======================")


video_file_name = path.basename(input_video)
video_file_name_without_extension = path.splitext(video_file_name)[0]


def extract_audio(force: bool):
    extracted_audio = path.join(
        video_directory, f"audio-{video_file_name_without_extension}.wav")

    if not (force) and path.exists(extracted_audio):
        print(f"audio has already been extracted ({extracted_audio})")
        return extracted_audio

    stream = ffmpeg.input(input_video)
    stream = ffmpeg.output(stream, extracted_audio)
    ffmpeg.run(stream, overwrite_output=True)
    return extracted_audio


def transcribe(audio):
    model = WhisperModel("small")
    segments, info = model.transcribe(audio, language=lang)
    language = info[0]
    print("Transcription language", info[0])
    # segments = list(segments)
    subtitle_segments = []
    for segment in segments:
        subtitle_segments.append(segment)
        # print(segment)
        print("[%.2fs -> %.2fs] %s" %
              (segment.start, segment.end, segment.text))
    return language, subtitle_segments


def format_time(seconds):

    hours = math.floor(seconds / 3600)
    seconds %= 3600
    minutes = math.floor(seconds / 60)
    seconds %= 60
    milliseconds = round((seconds - math.floor(seconds)) * 1000)
    seconds = math.floor(seconds)
    formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:01d},{milliseconds:03d}"

    return formatted_time


def generate_subtitle_file(language, segments):

    subtitle_file = path.join(video_directory,
                              f"sub-{video_file_name_without_extension}.{language}.srt")
    text = ""
    for index, segment in enumerate(segments):
        segment_start = format_time(segment.start)
        segment_end = format_time(segment.end)
        text += f"{str(index+1)} \n"
        text += f"{segment_start} --> {segment_end} \n"
        text += f"{segment.text} \n"
        text += "\n"

    f = open(subtitle_file, "w")
    f.write(text)
    f.close()

    return subtitle_file


def add_subtitle_to_video(soft_subtitle, subtitle_file,  subtitle_language):

    video_input_stream = ffmpeg.input(input_video)
    subtitle_input_stream = ffmpeg.input(subtitle_file)
    output_video = path.join(video_directory,
                             f"with-subtitles-{video_file_name_without_extension}.mp4")
    subtitle_track_title = path.basename(subtitle_file).replace(".srt", "")

    if soft_subtitle:
        stream = ffmpeg.output(
            video_input_stream, subtitle_input_stream, output_video, **{"c": "copy", "c:s": "mov_text"},
            **{"metadata:s:s:0": f"language={subtitle_language}",
               "metadata:s:s:0": f"title={subtitle_track_title}"}
        )
        ffmpeg.run(stream, overwrite_output=True)
    else:
        stream = ffmpeg.output(
            video_input_stream, output_video, vf=f"subtitles={subtitle_file}")
        ffmpeg.run(stream, overwrite_output=True)


def run():
    extracted_audio = extract_audio(isForced)
    language, segments = transcribe(audio=extracted_audio)
    subtitle_file = generate_subtitle_file(
        language=language,
        segments=segments
    )
    add_subtitle_to_video(
        soft_subtitle=True,
        subtitle_file=subtitle_file,
        subtitle_language=language
    )


run()
