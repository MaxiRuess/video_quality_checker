import streamlit as st 
import pandas as pd
import numpy as np
import ffmpeg
from fractions import Fraction
import subprocess
import json
from tqdm import tqdm
import os
import re


def get_video_properties(video_path):
    """
    Get properties of the video file using ffprobe.
    
    Args:
    video_path (str): The path to the video file.
    
    Returns:
    dict: A dictionary containing the video properties.
    """
    command = [
        'ffprobe', 
        '-v', 'error', 
        '-select_streams', 'v:0',
        '-show_entries', 'stream',
        '-of', 'json',
        video_path
    ]
    
    # Run the ffprobe process, decode stdout into utf-8 & convert to JSON
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    video_info = json.loads(result.stdout)
    
    # Extract the first video stream
    video_stream = video_info['streams'][0]

    # Calculate frame rate
    frame_rate_num, frame_rate_den = map(int, video_stream['r_frame_rate'].split('/'))
    frame_rate = frame_rate_num / frame_rate_den

    # Calculate display aspect ratio
    display_aspect_ratio = float(video_stream['display_aspect_ratio'].split(':')[0]) / float(video_stream['display_aspect_ratio'].split(':')[1])

    # Extract GOP size
    gop_m = gop_n = 0  # Default values if GOP size is not specified
    if 'tags' in video_stream and 'gop_size' in video_stream['tags']:
        gop_info = video_stream['tags']['gop_size'].split(',')
        gop_m = int(gop_info[0].split('=')[1])
        gop_n = int(gop_info[1].split('=')[1])

    video_properties = {
        'format_name': video_stream['codec_name'],  # e.g. 'h264', 'hevc', 'vp9', 'av1
        'format_level': video_stream['level'],
        'codec_name': video_stream['codec_name'],
        'format_profile': video_stream.get('profile', ''),
        'width': int(video_stream['width']),
        'height': int(video_stream['height']),
        'bit_rate': int(video_stream.get('bit_rate', '0')),
        'frame_rate': frame_rate,
        'display_aspect_ratio': display_aspect_ratio,
        'color_space': video_stream.get('color_space', ''),
        'chroma_subsampling': video_stream.get('pix_fmt', ''),
        'bit_depth': int(video_stream.get('bits_per_raw_sample', '8')),
        'scan_type': 'interlaced' if video_stream.get('field_order', 'progressive') != 'progressive' else 'progressive',
        'scan_order': 'TFF' if video_stream.get('field_order', 'bb') == 'tt' else 'BFF' if video_stream.get('field_order', 'tt') == 'bb' else 'Progressive',
        'gop_m': gop_m,
        'gop_n': gop_n,
        
    }
    
    return video_properties
    
def convert_video_to_requirements(input_video_path, output_video_path, 
                                  video_codec='h264_videotoolbox', resolution='1920x1080',
                                  bitrate='50M', audio_codec='pcm_s16le'):
    """Converts a video using ffmpeg, with options for customization.

    Args:
        input_video_path: Path to the input video file.
        output_video_path: Path for the converted output video file.
        video_codec: Video codec to use (default: 'h264_videotoolbox').
        resolution: Desired resolution (default: '1920x1080').
        bitrate: Target video bitrate (default: '50M').
        audio_codec: Audio codec to use (default: 'pcm_s16le').
    """

    command = [
        'ffmpeg',
        '-i', input_video_path,  
        '-c:v', video_codec,  
        '-profile:v', '4:2:2', 
        '-g', '12',  
        '-b:v', bitrate,  
        '-minrate', bitrate,
        '-maxrate', bitrate,  
        '-bufsize', bitrate,  
        '-vf', f'scale={resolution},setfield=mode=tff',  
        '-aspect', '16:9',  
        '-r', '25',  
        '-c:a', audio_codec,  
        '-ar', '48k', 
        '-ac', '2',  
        '-b:a', '1536k',  
    ]

    # Use hardware-specific pixel format if using h264_videotoolbox
    if video_codec == 'h264_videotoolbox':
        command.append('-pix_fmt')
        command.append('nv12')

    command.append(output_video_path) 

    # More robust error handling
    try:
         result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
         if result.returncode != 0:
             raise RuntimeError("ffmpeg conversion failed: {}".format(result.stderr))
         else:
             print("Video conversion completed successfully.")
    except (RuntimeError, subprocess.CalledProcessError) as err:
         print("Error during conversion:", err) 


st.title("Video Quality checker Tool")

uploaded_file = st.file_uploader("Choose a video...", type=["mp4", "mov", "avi", "mkv", "mxf"])

if uploaded_file is not None:
    temporary_location = f"./{uploaded_file.name}"
    
    with open(temporary_location, "wb") as f:
        f.write(uploaded_file.read())  

        
    video_properties = get_video_properties(temporary_location)
        

    st.write(video_properties)
    
    button = st.button("Convert to XDCAM HD422")
    
    if button:
        convert_video_to_requirements(temporary_location, "output.mxf")
        st.write("Conversion completed")
        st.write("Download the converted file")
        st.download_button(
            label="Download",
            data="output.mxf",
            file_name="output.mxf",
            mime="video/mxf"
        )

    
    
