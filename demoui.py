import pygame
import moviepy.editor as mp
import time
import os
import tempfile
import ctypes
import subprocess
import psutil
import hashlib
import json
import win32com.client  # For PowerPoint thumbnail generation
import pyautogui  # For sending keyboard commands to PowerPoint
import sys

# Initialize pygame and mixer
pygame.init()
pygame.joystick.init()
pygame.mixer.init()  # Initialize pygame mixer for audio

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080
MINIMIZED_WIDTH, MINIMIZED_HEIGHT = 560, 50  # Dimensions of the minimized window
FPS = 30
INACTIVITY_TIMEOUT = 5  # 5 seconds for inactivity
BGM_PATH = "bgm.mp3"

# Application states
STATE_LOADING = 'loading'        # New loading state
STATE_MAIN_MENU = 'main_menu'
STATE_PPT_MENU = 'ppt_menu'
STATE_MINIMIZED = 'minimized'
STATE_SHOW_BG2 = 'show_bg2'

# Set the initial state
current_state = STATE_LOADING    # Start with the loading state

# Screen setup
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Pygame Controller UI")
clock = pygame.time.Clock()

# Load images
bg_image = pygame.image.load("bg.jpg").convert()
bg2_image = pygame.image.load("bg2.jpg").convert()
btn1_image = pygame.image.load("btn1.jpg").convert_alpha()
btn2_image = pygame.image.load("btn2.jpg").convert_alpha()
btn3_image = pygame.image.load("btn3.jpg").convert_alpha()
btn4_image = pygame.image.load("btn4.jpg").convert_alpha()  # New button for PPT menu

# Button positioning and size
button_y = SCREEN_HEIGHT - int(SCREEN_HEIGHT / 5)  # Position buttons at 1/5 of the screen height from the bottom
btn1_rect = btn1_image.get_rect(center=(SCREEN_WIDTH // 5, button_y))
btn2_rect = btn2_image.get_rect(center=(2 * SCREEN_WIDTH // 5, button_y))
btn3_rect = btn3_image.get_rect(center=(3 * SCREEN_WIDTH // 5, button_y))
btn4_rect = btn4_image.get_rect(center=(4 * SCREEN_WIDTH // 5, button_y))

# Video files
vid1_path = "vid1.mp4"
vid2_path = "vid2.mp4"

# Cached audio file paths
audio_cache = {}

# Controller setup
controller = None
if pygame.joystick.get_count() > 0:
    controller = pygame.joystick.Joystick(0)
    controller.init()
    print("Controller detected:", controller.get_name())

# Variables
selected_button = 1  # 1 for btn1, 2 for btn2, 3 for btn3, 4 for btn4
last_activity_time = time.time()
bgm_playing = False

# For PPT menu
ppt_directory = os.path.dirname(os.path.realpath(__file__))
cache_file = os.path.join(ppt_directory, "thumbnail_cache.json")
ppt_files = []
thumbnails = {}
thumbnail_cache = {}
tiles_per_row = 4
rows_per_page = 3
tiles_per_page = tiles_per_row * rows_per_page
current_page = 0
ppt_selected_index = 0
toolbar_index = 0  # 0: No toolbar focus, 1: Prev Page, 2: Return to Main Menu, 3: Next Page
in_slideshow = False  # Flag for slideshow mode

# Colors and fonts for PPT menu and loading screen
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SELECTED_COLOR = (200, 0, 0)  # Red for selected background
NON_SELECTED_COLOR = (0, 0, 150)  # Blue for non-selected background
HIGHLIGHT_COLOR = (255, 215, 0)  # Highlight color for toolbar
TOOLBAR_COLOR = (50, 50, 50)
TEXT_COLOR = WHITE
font = pygame.font.Font("c:\Windows\Fonts\simhei.ttf", 24)
loading_font = pygame.font.Font(None, 60)  # Larger font for loading screen

# Function to calculate MD5 hash of a file
def calculate_md5(file_path):
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

# Define the path to PowerPoint executable
def get_powerpoint_path():
    possible_paths = [
        r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
        r"C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE",
        r"C:\Program Files\Microsoft Office\Office15\POWERPNT.EXE",
        r"C:\Program Files (x86)\Microsoft Office\Office15\POWERPNT.EXE",
        r"C:\Program Files\Microsoft Office\Office14\POWERPNT.EXE",
        r"C:\Program Files\Microsoft Office\Office12\POWERPNT.EXE",
        r"C:\Program Files (x86)\Microsoft Office\Office14\POWERPNT.EXE",
        r"C:\Program Files\Microsoft Office (x86)\Office12\POWERPNT.EXE"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

# Get PowerPoint path
powerpoint_path = get_powerpoint_path()

# Function to start PowerPoint slideshow
def start_ppt_slideshow(file_path):
    global in_slideshow
    if powerpoint_path and os.path.exists(file_path):
        # Start PowerPoint slideshow
        subprocess.Popen([powerpoint_path, "/s", file_path])
        in_slideshow = True

        # Start the controller mapping script
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ppt_controller.py")
        subprocess.Popen([sys.executable, script_path])
    else:
        print("PowerPoint executable not found. Please install PowerPoint or specify its path.")

# Function to monitor if PowerPoint is running
def is_ppt_running():
    return any("powerpnt" in process.name().lower() for process in psutil.process_iter(['name']))

# Function to bring Pygame window to the front
def bring_window_to_front():
    hwnd = pygame.display.get_wm_info()['window']
    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    ctypes.windll.user32.SetForegroundWindow(hwnd)

# Helper Functions
def reset_inactivity_timer():
    global last_activity_time
    last_activity_time = time.time()

def set_fullscreen_mode():
    global screen
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)

def set_minimized_mode():
    global screen
    screen = pygame.display.set_mode((MINIMIZED_WIDTH, MINIMIZED_HEIGHT), pygame.NOFRAME)
    # Calculate x-coordinate to center the window horizontally at the top
    x_position = (ctypes.windll.user32.GetSystemMetrics(0) - MINIMIZED_WIDTH) // 2
    y_position = 0  # Top of the screen

    # Move the window to the calculated position
    hwnd = pygame.display.get_wm_info()['window']
    ctypes.windll.user32.SetWindowPos(hwnd, None, x_position, y_position, 0, 0, 0x0001)

def open_explorer_folder():
    """Opens the folder where this program is located."""
    folder_path = os.path.dirname(os.path.abspath(__file__))
    subprocess.Popen(f'explorer "{folder_path}"')

def play_bgm():
    """Plays background music if it exists."""
    global bgm_playing
    if os.path.exists(BGM_PATH) and not bgm_playing:
        pygame.mixer.music.load(BGM_PATH)
        pygame.mixer.music.play(-1)  # Loop indefinitely
        bgm_playing = True

def stop_bgm():
    """Stops background music if playing."""
    global bgm_playing
    if bgm_playing:
        pygame.mixer.music.stop()
        bgm_playing = False

def get_audio_path_for_video(video_path):
    """Generate and cache audio for the given video, if not already cached."""
    if video_path not in audio_cache:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio_file:
            audio_cache[video_path] = tmp_audio_file.name
        clip = mp.VideoFileClip(video_path)
        clip.audio.write_audiofile(audio_cache[video_path])  # Write audio once
    return audio_cache[video_path]

def play_video_with_audio(video_path, return_message=None):
    """Play video with audio using pygame mixer for audio, and show a return message if specified."""
    clip = mp.VideoFileClip(video_path).resize((SCREEN_WIDTH, SCREEN_HEIGHT))
    
    # Load and play audio from the cached file path
    audio_path = get_audio_path_for_video(video_path)
    pygame.mixer.music.load(audio_path)
    pygame.mixer.music.play()
    
    for frame in clip.iter_frames(fps=FPS, dtype="uint8"):
        frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        screen.blit(pygame.transform.scale(frame_surface, (SCREEN_WIDTH, SCREEN_HEIGHT)), (0, 0))
    
        # Show return message if specified
        if return_message:
            font = pygame.font.SysFont(None, 60)
            text_surface = font.render(return_message, True, (255, 255, 255))  # White color
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100))
            screen.blit(text_surface, text_rect)
    
        pygame.display.flip()
        clock.tick(FPS)
    
        # Check for return to main screen
        for event in pygame.event.get():
            if event.type in (pygame.JOYBUTTONDOWN, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                pygame.mixer.music.stop()  # Stop audio playback
                clip.close()  # Close the video clip
                return
    
    pygame.mixer.music.stop()
    clip.close()

def play_vid1_with_message():
    """Play vid1 with 'Press anything on the joystick or click to continue' message."""
    clip = mp.VideoFileClip(vid1_path).resize((SCREEN_WIDTH, SCREEN_HEIGHT))
    
    # Load and play audio from the cached file path
    audio_path = get_audio_path_for_video(vid1_path)
    pygame.mixer.music.load(audio_path)
    pygame.mixer.music.play()
    
    for frame in clip.iter_frames(fps=FPS, dtype="uint8"):
        frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        screen.blit(pygame.transform.scale(frame_surface, (SCREEN_WIDTH, SCREEN_HEIGHT)), (0, 0))
    
        # Show message
        font = pygame.font.SysFont(None, 60)
        text_surface = font.render("Press anything on the joystick or click to continue", True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100))
        screen.blit(text_surface, text_rect)
    
        pygame.display.flip()
        clock.tick(FPS)
    
        # Check for interruption to exit video
        for event in pygame.event.get():
            if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION, pygame.JOYAXISMOTION, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                pygame.mixer.music.stop()
                clip.close()
                return
    
    pygame.mixer.music.stop()
    clip.close()

def show_bg2_screen():
    """Displays bg2.jpg and waits for the A button to return to the main screen."""
    global current_state
    current_state = STATE_SHOW_BG2
    screen.blit(bg2_image, (0, 0))

    # Render "Press A button to return to home" text in white
    font = pygame.font.SysFont(None, 60)
    text_surface = font.render("Press A button to return to home", True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100))
    screen.blit(text_surface, text_rect)
    pygame.display.flip()

# Movement and selection functions with confinement in PPT menu
def move_selection_left():
    global ppt_selected_index, toolbar_index
    if toolbar_index > 1:
        toolbar_index -= 1
    elif toolbar_index == 1:
        toolbar_index = 0  # Move focus back to grid
    elif toolbar_index == 0:
        # Calculate the bounds of the current page
        start_index = current_page * tiles_per_page
        if ppt_selected_index > start_index:
            ppt_selected_index -= 1

def move_selection_right():
    global ppt_selected_index, toolbar_index
    if toolbar_index == 0:
        # Calculate the end index of the current page
        end_index = min((current_page + 1) * tiles_per_page, len(ppt_files))
        if ppt_selected_index + 1 < end_index:
            ppt_selected_index += 1
    elif toolbar_index < 3:
        toolbar_index += 1

def move_selection_up():
    global ppt_selected_index, toolbar_index
    if toolbar_index == 0:
        # Check if already on the top row; if so, toggle to toolbar
        if (ppt_selected_index - (current_page * tiles_per_page)) < tiles_per_row:
            toolbar_index = 1
        else:
            ppt_selected_index -= tiles_per_row
    else:
        toolbar_index = 0  # Move back to grid

def move_selection_down():
    global ppt_selected_index, toolbar_index
    if toolbar_index == 0:
        # Calculate the bounds of the current page
        start_index = current_page * tiles_per_page
        end_index = min(start_index + tiles_per_page, len(ppt_files))
        max_index = end_index - 1
        if ppt_selected_index + tiles_per_row <= max_index:
            ppt_selected_index += tiles_per_row
        else:
            toolbar_index = 1  # Move to toolbar
    else:
        toolbar_index = 1  # Keep focus on toolbar

def select_current_item():
    global current_state
    if toolbar_index == 1:
        prev_page()
    elif toolbar_index == 2:
        current_state = STATE_MAIN_MENU  # Return to Main Menu
    elif toolbar_index == 3:
        next_page()
    else:
        ppt_path = os.path.join(ppt_directory, ppt_files[ppt_selected_index])
        start_ppt_slideshow(ppt_path)

# Navigation between pages in PPT menu
def next_page():
    global current_page, ppt_selected_index
    if (current_page + 1) * tiles_per_page < len(ppt_files):
        current_page += 1
        # Reset selection to first tile on the new page
        ppt_selected_index = current_page * tiles_per_page

def prev_page():
    global current_page, ppt_selected_index
    if current_page > 0:
        current_page -= 1
        # Reset selection to first tile on the previous page
        ppt_selected_index = current_page * tiles_per_page

# Helper function to draw toolbar at the bottom in PPT menu
def draw_toolbar():
    toolbar_height = 40
    toolbar_y = screen.get_height() - toolbar_height  # Position toolbar at the bottom
    pygame.draw.rect(screen, TOOLBAR_COLOR, (0, toolbar_y, screen.get_width(), toolbar_height))

    # Positions for toolbar buttons
    button_positions = [
        (screen.get_width() // 4, toolbar_y + toolbar_height // 2),  # Previous Page
        (screen.get_width() // 2, toolbar_y + toolbar_height // 2),  # Return to Main Menu
        (3 * screen.get_width() // 4, toolbar_y + toolbar_height // 2)  # Next Page
    ]

    # Draw "Previous Page" button
    prev_color = HIGHLIGHT_COLOR if toolbar_index == 1 else WHITE
    prev_button = font.render("Previous Page", True, prev_color)
    prev_rect = prev_button.get_rect(center=button_positions[0])
    screen.blit(prev_button, prev_rect)

    # Draw "Return to Main Menu" button
    return_color = HIGHLIGHT_COLOR if toolbar_index == 2 else WHITE
    return_button = font.render("Return to Main Menu", True, return_color)
    return_rect = return_button.get_rect(center=button_positions[1])
    screen.blit(return_button, return_rect)

    # Draw "Next Page" button
    next_color = HIGHLIGHT_COLOR if toolbar_index == 3 else WHITE
    next_button = font.render("Next Page", True, next_color)
    next_rect = next_button.get_rect(center=button_positions[2])
    screen.blit(next_button, next_rect)

    return prev_rect, return_rect, next_rect

def draw_ppt_menu():
    screen.fill(BLACK)
    prev_rect, return_rect, next_rect = draw_toolbar()

    # Calculate tile and thumbnail sizes dynamically
    tile_width = screen.get_width() // tiles_per_row - 20
    tile_height = tile_width * 9 // 16 + 40  # 16:9 aspect ratio for thumbnail + space for text
    thumbnail_width = tile_width
    thumbnail_height = tile_width * 9 // 16  # Maintain 16:9 aspect ratio

    # Display tiles on the current page
    start_index = current_page * tiles_per_page
    end_index = min(start_index + tiles_per_page, len(ppt_files))
    visible_tiles = end_index - start_index  # Number of visible tiles

    for i, file in enumerate(ppt_files[start_index:end_index]):
        actual_index = start_index + i
        tile_x = (i % tiles_per_row) * (tile_width + 20) + 10
        tile_y = (i // tiles_per_row) * (tile_height + 20) + 10  # Space above tiles
        tile_rect = pygame.Rect(tile_x, tile_y, tile_width, tile_height)

        color = SELECTED_COLOR if actual_index == ppt_selected_index and toolbar_index == 0 else NON_SELECTED_COLOR
        pygame.draw.rect(screen, color, tile_rect)

        # Draw thumbnail if available
        thumbnail = thumbnails.get(file)
        if thumbnail:
            # Scale the thumbnail to fit within the tile dynamically
            thumbnail_resized = pygame.transform.scale(thumbnail, (thumbnail_width, thumbnail_height))
            thumbnail_rect = thumbnail_resized.get_rect(center=(tile_rect.centerx, tile_rect.y + thumbnail_height // 2))
            screen.blit(thumbnail_resized, thumbnail_rect.topleft)

        display_name = os.path.splitext(file)[0]  # Remove extension for display
        text_surface = font.render(display_name, True, TEXT_COLOR)

        # Display filename below thumbnail
        text_y = tile_rect.y + thumbnail_height + 10
        clipped_text = text_surface.subsurface(0, 0, min(tile_rect.width - 20, text_surface.get_width()), text_surface.get_height())
        screen.blit(clipped_text, (tile_rect.x + 10, text_y))

# Initialize variables for loading screen
loading_started = False
loading_index = 0

# Main loop
running = True
while running:
    if current_state == STATE_LOADING:
        if not loading_started:
            # Initialize loading variables
            loading_started = True
            loading_index = 0
            # Load or initialize the thumbnail cache
            if os.path.exists(cache_file):
                with open(cache_file, "r") as f:
                    thumbnail_cache = json.load(f)
            else:
                thumbnail_cache = {}
            # Initialize ppt_files as a list of PowerPoint files in the directory
            ppt_files = [
                f for f in os.listdir(ppt_directory)
                if f.endswith(".ppt") or f.endswith(".pptx")
            ]
            # Initialize thumbnails dict
            thumbnails = {}
            total_files = len(ppt_files)
            # Initialize PowerPoint application
            ppt_app = win32com.client.Dispatch("PowerPoint.Application")
            ppt_app.Visible = 1
            # Clear the screen
            screen.fill(BLACK)
            # Display initial loading message
            loading_text = loading_font.render("Loading DEMO UI... 0%", True, WHITE)
            text_rect = loading_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(loading_text, text_rect)
            pygame.display.flip()
        else:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            # Process one thumbnail per iteration
            if loading_index < len(ppt_files):
                filename = ppt_files[loading_index]
                pptx_path = os.path.join(ppt_directory, filename)
                file_md5 = calculate_md5(pptx_path)
                thumbnail_filename = f"{os.path.splitext(filename)[0]}_thumbnail_{file_md5}.jpg"
                output_image = os.path.join(ppt_directory, thumbnail_filename)
                # Check if a cached thumbnail with the correct MD5 already exists
                if thumbnail_cache.get(filename) == file_md5 and os.path.exists(output_image):
                    thumbnail_image = pygame.image.load(output_image)
                    thumbnails[filename] = thumbnail_image
                else:
                    try:
                        # Open the PowerPoint file and export the first slide as a thumbnail
                        presentation = ppt_app.Presentations.Open(pptx_path, WithWindow=False)
                        slide = presentation.Slides[1]
                        slide.Export(output_image, "JPG", 640, 360)
                        presentation.Close()
                        # Load the new thumbnail into pygame
                        thumbnail_image = pygame.image.load(output_image)
                        thumbnails[filename] = thumbnail_image
                        # Update cache with the new MD5
                        thumbnail_cache[filename] = file_md5
                    except Exception as e:
                        print(f"Failed to create thumbnail for {filename}: {e}")
                # Update loading_index
                loading_index += 1
                # Update the display to show progress
                progress = int((loading_index / total_files) * 100)
                screen.fill(BLACK)
                loading_message = f"Loading DEMO UI... {progress}%"
                loading_text = loading_font.render(loading_message, True, WHITE)
                text_rect = loading_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                screen.blit(loading_text, text_rect)
                pygame.display.flip()
            else:
                # All thumbnails processed
                ppt_app.Quit()
                # Save the updated cache
                with open(cache_file, "w") as f:
                    json.dump(thumbnail_cache, f)
                # Initialize variables for PPT menu
                ppt_selected_index = 0
                current_page = 0
                in_slideshow = False
                toolbar_index = 0
                current_state = STATE_MAIN_MENU
    elif current_state == STATE_MAIN_MENU:
        screen.blit(bg_image, (0, 0))
        # Draw buttons with a green border around the selected button
        buttons = [btn1_rect, btn2_rect, btn3_rect, btn4_rect]
        for idx, btn_rect in enumerate(buttons, 1):
            if selected_button == idx:
                pygame.draw.rect(screen, (0, 255, 0), btn_rect.inflate(10, 10), 3)
            screen.blit([btn1_image, btn2_image, btn3_image, btn4_image][idx - 1], btn_rect.topleft)
    elif current_state == STATE_MINIMIZED:
        # Display message in minimized mode
        screen.fill((50, 50, 50))  # Dark background
        font = pygame.font.SysFont(None, 40)
        text_surface = font.render("Press D-pad Up to return to fullscreen", True, (255, 255, 255))
        screen.blit(text_surface, (10, 10))
    elif current_state == STATE_SHOW_BG2:
        # Already drawn in show_bg2_screen()
        pass
    elif current_state == STATE_PPT_MENU:
        draw_ppt_menu()
        if in_slideshow and not is_ppt_running():
            in_slideshow = False  # Exit slideshow mode if PowerPoint closes
            bring_window_to_front()

    # Check inactivity (do not check inactivity while in PPT menu)
    if current_state in (STATE_MAIN_MENU, STATE_MINIMIZED) and time.time() - last_activity_time > INACTIVITY_TIMEOUT:
        if current_state == STATE_MINIMIZED:
            stop_bgm()
            set_fullscreen_mode()
            current_state = STATE_MAIN_MENU
        play_vid1_with_message()
        reset_inactivity_timer()
    
    pygame.display.flip()
    clock.tick(FPS)

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif current_state == STATE_MAIN_MENU:
            # Handle main menu events
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_RIGHT:
                    selected_button = min(4, selected_button + 1)
                elif event.key == pygame.K_LEFT:
                    selected_button = max(1, selected_button - 1)
                elif event.key == pygame.K_RETURN:
                    # Simulate pressing the A button
                    event = pygame.event.Event(pygame.JOYBUTTONDOWN, {'button': 0})
                    pygame.event.post(event)
            elif event.type == pygame.JOYHATMOTION:
                if event.value == (-1, 0):  # Left on D-pad
                    selected_button = max(1, selected_button - 1)
                elif event.value == (1, 0):  # Right on D-pad
                    selected_button = min(4, selected_button + 1)
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:  # A button (select)
                    if selected_button == 1:
                        set_minimized_mode()
                        play_bgm()
                        current_state = STATE_MINIMIZED
                    elif selected_button == 2:
                        play_video_with_audio(vid2_path, "Press A Button to return to home")
                    elif selected_button == 3:
                        show_bg2_screen()
                    elif selected_button == 4:
                        # Reset variables for PPT menu
                        ppt_selected_index = current_page * tiles_per_page
                        toolbar_index = 0
                        current_state = STATE_PPT_MENU
                    reset_inactivity_timer()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if btn1_rect.collidepoint(event.pos):
                    selected_button = 1
                    set_minimized_mode()
                    play_bgm()
                    current_state = STATE_MINIMIZED
                elif btn2_rect.collidepoint(event.pos):
                    selected_button = 2
                    play_video_with_audio(vid2_path, "Press A Button to return to home")
                elif btn3_rect.collidepoint(event.pos):
                    selected_button = 3
                    show_bg2_screen()
                elif btn4_rect.collidepoint(event.pos):
                    selected_button = 4
                    # Reset variables for PPT menu
                    ppt_selected_index = current_page * tiles_per_page
                    toolbar_index = 0
                    current_state = STATE_PPT_MENU
                reset_inactivity_timer()
            elif event.type in (pygame.KEYDOWN, pygame.JOYBUTTONDOWN, pygame.MOUSEBUTTONDOWN):
                reset_inactivity_timer()

        elif current_state == STATE_MINIMIZED:
            # Handle minimized mode events
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN, pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION, pygame.JOYAXISMOTION):
                reset_inactivity_timer()
                # Check for events that return to fullscreen
                if event.type == pygame.MOUSEBUTTONDOWN:
                    stop_bgm()
                    set_fullscreen_mode()
                    current_state = STATE_MAIN_MENU
                elif event.type == pygame.JOYHATMOTION and event.value == (0, 1):  # Up on D-pad
                    stop_bgm()
                    set_fullscreen_mode()
                    current_state = STATE_MAIN_MENU
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    stop_bgm()
                    set_fullscreen_mode()
                    current_state = STATE_MAIN_MENU

        elif current_state == STATE_SHOW_BG2:
            # Handle events to return from bg2 screen
            if event.type == pygame.JOYBUTTONDOWN and event.button == 0:
                current_state = STATE_MAIN_MENU
                reset_inactivity_timer()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                current_state = STATE_MAIN_MENU
                reset_inactivity_timer()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                current_state = STATE_MAIN_MENU
                reset_inactivity_timer()

        elif current_state == STATE_PPT_MENU:
            # Handle PPT menu events
            if in_slideshow:
                # Do not handle controller inputs here; the separate script does this
                # Just check if PowerPoint has exited
                if not is_ppt_running():
                    in_slideshow = False
                    bring_window_to_front()
            else:
                # Handle PPT menu navigation
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        current_state = STATE_MAIN_MENU
                    elif event.key == pygame.K_RIGHT:
                        move_selection_right()
                    elif event.key == pygame.K_LEFT:
                        move_selection_left()
                    elif event.key == pygame.K_DOWN:
                        move_selection_down()
                    elif event.key == pygame.K_UP:
                        move_selection_up()
                    elif event.key == pygame.K_RETURN:
                        select_current_item()
                elif event.type == pygame.JOYHATMOTION:
                    if event.value == (-1, 0):  # Left
                        move_selection_left()
                    elif event.value == (1, 0):  # Right
                        move_selection_right()
                    elif event.value == (0, -1):  # Down
                        move_selection_down()
                    elif event.value == (0, 1):  # Up
                        move_selection_up()
                elif event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 0:  # A button
                        select_current_item()
                    elif event.button == 1:  # B button
                        current_state = STATE_MAIN_MENU
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Optional: Add mouse interaction with toolbar buttons
                    mouse_pos = event.pos
                    toolbar_buttons = draw_toolbar()
                    for idx, button_rect in enumerate(toolbar_buttons, 1):
                        if button_rect.collidepoint(mouse_pos):
                            if idx == 1:
                                prev_page()
                            elif idx == 2:
                                current_state = STATE_MAIN_MENU
                            elif idx == 3:
                                next_page()
                            break

pygame.quit()
