import sqlite3
import pygame
import time
import re  # Import the re module for regular expression
from sys import exit

import pygame_menu as pm

# Connecting to the database
def dict_factor(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

conn = sqlite3.connect("President.db")
conn.row_factory = dict_factor

def create_tables():
    conn.execute(''' CREATE TABLE if not exists Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    guest BOOLEAN DEFAULT false,
    sound_effects BOOLEAN DEFAULT true,
    notifications BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT current_timestamp);''')
    conn.commit()
    
    conn.execute('''CREATE TABLE if not exists GameSettings (
    setting_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER REFERENCES Users(user_id),
    rounds INTEGER DEFAULT 3,
    ai_difficulty TEXT DEFAULT 'Medium');''')
    conn.commit()
    
    conn.execute('''CREATE TABLE if not exists GameResults (
    results_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER REFERENCES Users(user_id),
    rank TEXT NOT NULL,
    total_games INTEGER DEFAULT 0,
    played_at TIMESTAMP DEFAULT current_timestamp);''')
    conn.commit()
    
    conn.execute('''CREATE TABLE if not exists Leaderboard (
    leaderboard_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER REFERENCES Users(user_id),
    total_games INTEGER REFERENCES GameResults(total_games),
    num_Pres INTEGER DEFAULT 0,
    num_V_Pres INTEGER DEFAULT 0,
    num_Mid INTEGER DEFAULT 0,
    num_V_Bum INTEGER DEFAULT 0,
    num_Bum INTEGER DEFAULT 0);''')
    conn.commit() 

create_tables()

# Create a new user account
def create_user(username, password):
    # Check for invalid characters using a regular expression
    if not re.match("^[A-Za-z0-9_]+$", username):
        return "Invalid username format. Use only letters, numbers, and \nunderscores."
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        return "Username already exists. Please choose a different \n username."
    else:
        cursor.execute("INSERT INTO Users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return "Account created successfully."

# Check if the user exists and password matches
def find_user(username, password):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ? AND password = ?", (username, password))
    return cursor.fetchone()

# Create a new guest user (if necessary)
def create_guest_user(guest_name):
    # Check if the guest name already exists in the Users table
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ?", (guest_name,))
    existing_user = cursor.fetchone()

    if existing_user:
        # Return the guest message if the guest name is already taken
        return "Guest name already exists. \n Please choose a different \n name."
    else:
        # Insert the guest name into the Users table if it doesn't exist
        cursor.execute("INSERT INTO Users (username, password, guest) VALUES (?, ?, ?)", (guest_name, '', True))
        conn.commit()
        return ""

# Function to update the password for the forgot password feature
def update_password(username, new_password):
    cursor = conn.cursor()
    # Retrieve the current password for the user
    cursor.execute("SELECT password FROM Users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        current_password = existing_user["password"]
        
        # Check if the new password is the same as the current one
        if current_password == new_password:
            return "Password is the same as before. Please choose a \n different password."
        
        # Check password length
        if len(new_password) < 8:
            return "Password is too short. It must be at least 8 \n characters long."
        
        # Update the password in the database
        cursor.execute("UPDATE Users SET password = ? WHERE username = ?", (new_password, username))
        conn.commit()
        return "Password updated successfully. Please log in."
    else:
        return "Username not found."

# Pygame setup
pygame.init()
screen = pygame.display.set_mode((1400, 780))
pygame.display.set_caption("President")
clock = pygame.time.Clock()

pygame_icon = pygame.image.load('Images/game_icon.png').convert_alpha()
pygame.display.set_icon(pygame_icon)
# Load images
front_page_image = pygame.image.load("Images/Front_Page.jpg").convert_alpha()
game_background = pygame.image.load("Images/Background.jpg").convert_alpha()

# Load the back button image
back_button_image = pygame.image.load("Images/download.svg").convert_alpha()
back_button_resized = pygame.transform.smoothscale(back_button_image, (50, 50))  # Adjust size as needed

# Define the back button rectangle (for click detection)
back_button_rect = pygame.Rect(10, 10, 50, 50)  # Set position and size for the back button

# Regular font sizes
font_reg_big = pygame.font.Font('Font/Sansation_Regular.ttf', 60)
font_reg_medium = pygame.font.Font('Font/Sansation_Regular.ttf', 40)
font_reg_small = pygame.font.Font('Font/Sansation_Regular.ttf', 20)

# Italic font sizes
font_italic_big = pygame.font.Font('Font/Sansation_Italic.ttf', 60)
font_italic_medium = pygame.font.Font('Font/Sansation_Italic.ttf', 40)
font_italic_small = pygame.font.Font('Font/Sansation_Italic.ttf', 25)

# Bold font sizes
font_bold_big = pygame.font.Font('Font/Sansation_Bold.ttf', 60)
font_bold_medium = pygame.font.Font('Font/Sansation_Bold.ttf', 40)
font_bold_small = pygame.font.Font('Font/Sansation_Bold.ttf', 25)

# Bold Italic font sizes
font_It_bold_big = pygame.font.Font('Font/Sansation_Bold_Italic.ttf', 60)
font_It_bold_medium = pygame.font.Font('Font/Sansation_Bold_Italic.ttf', 35)
font_It_bold_small = pygame.font.Font('Font/Sansation_Bold_Italic.ttf', 25)

# State variable to track which page to display: login or signup
current_page = "login"
show_front_page = True  # This controls whether the front page is shown first

# Input field variables for Login/Login as a guest
username_text = ''
password_text = ''
name_text = ''
guest_message = ''
login_message = ''
show_blank_page = False # Only trigger for guest login

# Input field variables for sign-up
signup_username_text = ''
signup_password_text = ''
signup_message = ''

# Colors for input fields
color_active = pygame.Color('gray27')
color_passive = pygame.Color('Black') 
color_username = color_passive
color_password = color_passive 
color_name = color_passive

# Input field rectangles
username_input_rect = pygame.Rect(350, 160, 240, 32)
password_input_rect = pygame.Rect(350, 260, 240, 32)
name_input_rect = pygame.Rect(1000, 160, 240, 32)

# Sign up fields
signup_username_input_rect = pygame.Rect(650, 180, 240, 32)
signup_password_input_rect = pygame.Rect(650, 250, 240, 32)
signup_submit_button_rect = pygame.Rect(600, 450, 140, 50) 

# Submit button rectangles
submit_button_rect_1 = pygame.Rect(200, 450, 140, 50)  # User login submit button
submit_button_rect_2 = pygame.Rect(950, 450, 140, 50)  # Guest login submit button

signup_button_rect = pygame.Rect(350, 550, 240, 50)  # Sign Up button on the login page

# Labels
login_text = font_bold_big.render('Log in', True, "white")
username_label = font_reg_medium.render('Username: ', True, "white")
password_label = font_reg_medium.render('Password: ', True, "white")
submit_button_text = font_bold_medium.render('Submit', True, "black")
guest_text = font_bold_big.render('Guest', True, "white")
name_label = font_reg_medium.render('Name: ', True, "white")
signup_text = font_bold_big.render('Sign Up', True, "white")
signup_button_text = font_bold_small.render('New to President? Sign Up Now!', True, "red")

# Calculate the width and height of the signup button text
signup_button_width, signup_button_height = font_reg_medium.size("New to President! Sign Up Now!")

## Adjust the signup button rect to cover the entire text
signup_button_rect = pygame.Rect(submit_button_rect_1.x, submit_button_rect_1.y + 60, signup_button_width, signup_button_height)

# Handle active input field
active_field = None

# Screen dimensions
screen_width = 1400
screen_height = 780

# Calculate the central x-position for the input boxes
input_box_width = 240
label_to_input_gap = 20  # Distance between label and input box
total_width = 200 + input_box_width + label_to_input_gap  # 200 is an estimated label width

center_x_position = (screen_width - total_width) // 2
input_box_x_position = center_x_position + 200 + label_to_input_gap

# Reposition the input rectangles for the Forgot Password page to be centered
forgot_password_username_rect = pygame.Rect(input_box_x_position, 180, input_box_width, 32)
forgot_password_new_password_rect = pygame.Rect(input_box_x_position, 250, input_box_width, 32)
forgot_password_confirm_password_rect = pygame.Rect(input_box_x_position, 320, input_box_width, 32)
forgot_password_submit_button_rect = pygame.Rect((screen_width - 140) // 2, 480, 140, 50) # Center the submit button

# Define the "Forgot Password" button rectangle
forgot_password_button_rect = pygame.Rect(150, 600, 240, 50)
forgot_password_button_text = font_bold_small.render('Forgot Password?', True, "white")

# Variables for Forgot Password Page
forgot_password_username = ''
forgot_password_new_password = ''
forgot_password_confirm_password = ''
forgot_password_message = ''

# Colors for input fields
color_fp_username = color_passive
color_fp_new_password = color_passive
color_fp_confirm_password = color_passive

# fp labels
forgot_password_label = font_bold_big.render('Forgot Password', True, "white")
fp_username_label = font_reg_medium.render('Username:', True, "white")
fp_new_password_label = font_reg_medium.render('New Password:', True, "white")
fp_confirm_password_label = font_reg_medium.render('Confirm Password:', True, "white")

# Menu
show_menu = False  # Controls when to display the main menu
menu_options = ['Play Game', 'Leaderboard', 'Settings', 'Help']
menu_selected = None
hovered_option = None # To track which option is hovered

# Function to display the main menu with hover highlighting and clickable icons
def draw_menu():
    global text_x_position, hovered_option # Add hovered_option to global variables
    screen.blit(game_background, (0, 0))

    # Define the X position for icons and text in a single row
    icon_x_position = screen.get_width() // 2 - 150  # Adjust X position for icons
    text_x_position = icon_x_position + 80  # Adjust X position for text (after the icon)

    mouse_pos = pygame.mouse.get_pos()  # Get the current mouse position

    # Loop through each menu option and draw both text and the icon
    for i, option in enumerate(menu_options):
        # Change the text color to light blue if hovered, else keep white
        if hovered_option == i:
            option_surface = font_bold_medium.render(option, True, (173, 216, 230))  # Light blue when hovered
        else:
            option_surface = font_bold_medium.render(option, True, (255, 255, 255))  # White when not hovered

        # Get the size of the text and icon
        option_width, option_height = font_bold_medium.size(option)
        icon = menu_icons[i]
        icon_width, icon_height = icon.get_size()

        # Y position for each option
        y_position = 250 + i * 100

        # Create clickable rectangles for both icon and text
        icon_rect = pygame.Rect(icon_x_position, y_position, icon_width, icon_height)
        text_rect = pygame.Rect(text_x_position, y_position, option_width, option_height)

        # Blit the icon and the text in a single horizontal line
        screen.blit(icon, (icon_x_position, y_position))  # Display the icon
        screen.blit(option_surface, (text_x_position, y_position + (icon_height - option_height) // 2))  # Align text vertically with icon

        # Check if the icon or text is hovered and update hovered_option
        if icon_rect.collidepoint(mouse_pos) or text_rect.collidepoint(mouse_pos):
            hovered_option = i

    pygame.display.flip()

# Handle mouse clicks to make icons and text clickable
def handle_menu_click(mouse_pos):
    global menu_selected
    # Define the X position for icons and text (similar to draw_menu)
    icon_x_position = screen.get_width() // 2 - 150
    text_x_position = icon_x_position + 80

    for i, option in enumerate(menu_options):
        option_width, option_height = font_bold_medium.size(option)
        icon_width, icon_height = menu_icons[i].get_size()

        y_position = 250 + i * 100

        # Create clickable rectangles for both icon and text
        icon_rect = pygame.Rect(icon_x_position, y_position, icon_width, icon_height)
        text_rect = pygame.Rect(text_x_position, y_position, option_width, option_height)

        # Check if the mouse clicked on the icon or text
        if icon_rect.collidepoint(mouse_pos) or text_rect.collidepoint(mouse_pos):
            menu_selected = option  # Set the selected menu option
            break

# Function to handle hover detection
def check_hover():
    global hovered_option
    mouse_pos = pygame.mouse.get_pos()

    # Define the X position for the text (same as in draw_menu)
    icon_x_position = screen.get_width() // 2 - 150
    text_x_position = icon_x_position + 80

    for i, option in enumerate(menu_options):
        option_width, option_height = font_bold_medium.size(option)
        icon_height = menu_icons[i].get_height()

        # Y position for each option
        y_position = 250 + i * 100
        
        # Check if the mouse is within the bounds of the text (hovering)
        if text_x_position <= mouse_pos[0] <= text_x_position + option_width and \
           y_position <= mouse_pos[1] <= y_position + option_height:
            hovered_option = i  # Set the hovered option index
            return
    hovered_option = None  # Reset hover if no option is hovered

# Function to display the selected screen when a menu option is clicked
def draw_selected_screen(selection):
    screen.blit(game_background, (0, 0))

    # Check the selected option and render the appropriate screen
    if selection == "Play Game":
        pygame.display.set_caption("Game Preferences")
        draw_game_preferences()  # Call the game preferences screen
    else:
        # Display the generic message for other screens
        selected_text = f"Welcome to the {selection} screen"
        selected_surface = font_bold_medium.render(selected_text, True, (255, 255, 255))
        screen.blit(selected_surface, (screen.get_width() // 2 - selected_surface.get_width() // 2, screen.get_height() // 2))

    # Display the back button for all screens
    screen.blit(back_button_resized, back_button_rect.topleft) 
    pygame.display.flip()
    
# Menu Option Icons
play_button = pygame.image.load("Images/play2.png").convert_alpha()
leaderboard_button = pygame.image.load("Images/medal.png").convert_alpha()
help_button = pygame.image.load("Images/help_button.png").convert_alpha()
settings_button = pygame.image.load("Images/settings_button.png").convert_alpha()

# Resize the icons to match the menu size (optional)
icon_size = (50, 50)  

# Smooth scaling applied to each icon
play_button = pygame.transform.smoothscale(play_button, icon_size)
leaderboard_button = pygame.transform.smoothscale(leaderboard_button, icon_size)
help_button = pygame.transform.smoothscale(help_button, icon_size)
settings_button = pygame.transform.smoothscale(settings_button, icon_size)

menu_icons = [play_button, leaderboard_button, settings_button, help_button]

# Function to show the front page before the main menu
def show_front_page_screen():
    screen.blit(front_page_image, (0, 0))  # Display front page image
    pygame.display.flip()
    time.sleep(3)  # Show front page for 3 seconds 

# Define colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)

# Variables for game settings
rounds = 5
difficulty_options = [("Easy", "Easy"), ("Medium", "Medium"), ("Hard", "Hard")]
selected_difficulty = difficulty_options[1][1]  # Default to "Medium"
rounds_label = None

# Functions to modify rounds and set difficulty
def increment_rounds():
    global rounds, rounds_label
    if rounds < 50:  # Check if current rounds are less than the maximum
        rounds += 1
        rounds_label.set_title(f"{rounds} Rounds")  # Update label text immediately

def decrement_rounds():
    global rounds, rounds_label
    rounds = max(1, rounds - 1)  # Prevent rounds from going below 1
    rounds_label.set_title(f"{rounds} Rounds")  # Update label text immediately
            
def set_difficulty(selected, value):
    global selected_difficulty
    selected_difficulty = value  # Update selected difficulty

# Function to save game preferences to the GameSettings table
def save_game_preferences(user_id, rounds, ai_difficulty):
    cursor = conn.cursor()

    # Check if the user already has game settings
    cursor.execute("SELECT * FROM GameSettings WHERE user_id = ?", (user_id,))
    existing_settings = cursor.fetchone()

    if existing_settings:
        cursor.execute("""
            UPDATE GameSettings
            SET rounds = ?, ai_difficulty = ?
            WHERE user_id = ?
        """, (rounds, ai_difficulty, user_id))
    else:
        cursor.execute("""
            INSERT INTO GameSettings (user_id, rounds, ai_difficulty)
            VALUES (?, ?, ?)
        """, (user_id, rounds, ai_difficulty))

    conn.commit()  
    return "Game preferences saved successfully."

# Function to start the game with the selected settings
def start_game():
    global user_id 
    save_game_preferences(user_id, rounds, selected_difficulty)

theme = pm.themes.THEME_DARK.copy()
theme.widget_font = 'Arial'  # Replace with a font supporting Unicode
preferences_menu = pm.Menu(title="Game Preferences", width=700, height=600, theme=theme)

# Rounds selection controls
preferences_menu.add.label("Select Number of Rounds", font_name = font_bold_medium)
preferences_menu.add.button('\u25B2', increment_rounds)  # Up button
rounds_label = preferences_menu.add.label(f"{rounds} Rounds", font_name = font_reg_medium)  # Label
preferences_menu.add.button('\u25BC', decrement_rounds)  # Down button


# Dropdown for AI difficulty selection
preferences_menu.add.label("Select AI Difficulty", font_name = font_bold_medium)
preferences_menu.add.dropselect(title="Difficulty:", font_name = font_bold_medium, items=difficulty_options, default=1, onchange=set_difficulty)

# Button to confirm and start the game
preferences_menu.add.button("Let's Play!", start_game, font_name = font_bold_medium, font_color=WHITE, background_color=GREEN)

def draw_background():
    screen.blit(game_background, (0, 0))

# Main loop to display the preferences menu
def draw_game_preferences():
    pygame.display.set_caption("Game Preferences")
    preferences_menu.mainloop(screen, bgfun=draw_background)
    
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
    
        if show_menu:
            check_hover()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                handle_menu_click(mouse_pos) # Handle clicking on icons and text
                
                # Check if the back button is clicked on the selected screen
                if menu_selected and back_button_rect.collidepoint(mouse_pos):
                    menu_selected = None  # Go back to the main menu
                elif menu_selected == "Play Game":
                    draw_game_preferences()
                
                for i, option in enumerate(menu_options):
                    option_surface = font_bold_medium.render(option, True, (255, 255, 255))

                    # Get the size of the text to calculate the rectangle size
                    option_width, option_height = font_bold_medium.size(option)
                    option_rect = pygame.Rect(
                        screen.get_width() // 2 - option_width // 2 - 10,
                        250 + i * 100,
                        option_width + 20,
                        option_height + 10
                    )

                    if option_rect.collidepoint(mouse_pos):
                        menu_selected = option  # Set the selected menu option
                             
        if show_front_page:
            show_front_page_screen()
            show_front_page = False
            continue # Skip to the next frame (so login screen shows next)
        else:
        # Check for mouse click events to set active_field
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                
                if current_page == "login":
                    if username_input_rect.collidepoint(mouse_pos):
                        active_field = 'username'
                    elif password_input_rect.collidepoint(mouse_pos):
                        active_field = 'password'
                    elif name_input_rect.collidepoint(mouse_pos):
                        active_field = 'name'
                    elif signup_button_rect.collidepoint(mouse_pos):
                        current_page = "signup"
                        active_field = None
                        signup_username_text = signup_password_text = signup_message = ''
                        login_message = ''
                    elif forgot_password_button_rect.collidepoint(mouse_pos):
                        current_page = "forgot_password"
                        active_field = None
                        
                    # Handle user login submission (messages on the same screen)
                    elif submit_button_rect_1.collidepoint(mouse_pos):
                        if username_text and password_text:
                            user = find_user(username_text, password_text)
                            if user:
                                global user_id
                                user_id = user["user_id"]
                                
                                login_message = "Login Successful!"
                                guest_message = ''
                                show_menu = True
                                pygame.display.set_caption("Main Menu")
                            else:
                                login_message = "Invalid username or password!"
                                guest_message = ''
                        else:
                            login_message = "Please enter both username and password!"
                            guest_message = ''
                            
                    if submit_button_rect_2.collidepoint(mouse_pos):
                        if name_text:
                            guest_message = create_guest_user(name_text)
                            if guest_message:
                                show_menu = False  # Stay on the same screen if name already exists
                            else:
                                guest_message = f"Logged in as Guest: {name_text}"
                                show_menu = True  # Trigger to show black page for guest login
                                pygame.display.set_caption("Main Menu")
                        else:
                            guest_message = "Please enter a name for \n guest login."
                           
                elif current_page == "signup":
                    if signup_username_input_rect.collidepoint(mouse_pos):
                        active_field = 'signup_username'
                    elif signup_password_input_rect.collidepoint(mouse_pos):
                        active_field = 'signup_password'
                    elif signup_submit_button_rect.collidepoint(mouse_pos):
                        if signup_username_text and signup_password_text:
                            signup_message = create_user(signup_username_text, signup_password_text)
                            if signup_message == "Account created successfully.":
                                signup_username_text = signup_password_text = ''
                                current_page = "login"
                                signup_message = ''
                                login_message = "Account created successfully. Please log in."
                                active_field = None
                        else:
                            signup_message = "Please fill out both fields."
                            
                    # Check if the back button is clicked
                    elif pygame.Rect(10, 10, 100, 100).collidepoint(mouse_pos):
                        current_page = "login"
                        signup_username_text = signup_password_text = ''
                        signup_message = ''
                        active_field = None

                elif current_page == "forgot_password":
                    if forgot_password_username_rect.collidepoint(mouse_pos):
                        active_field = 'forgot_password_username'
                    elif forgot_password_new_password_rect.collidepoint(mouse_pos):
                        active_field = 'forgot_password_new_password'
                    elif forgot_password_confirm_password_rect.collidepoint(mouse_pos):
                        active_field = 'forgot_password_confirm_password'
                    elif forgot_password_submit_button_rect.collidepoint(mouse_pos):
                        if forgot_password_username and forgot_password_new_password and forgot_password_confirm_password:
                            if forgot_password_new_password == forgot_password_confirm_password:
                                forgot_password_message = update_password(forgot_password_username, forgot_password_new_password)
                                if "successfully" in forgot_password_message:
                                    current_page = "login"
                                    login_message = "Password updated. Please log in."
                                    active_field = None
                            else:
                                forgot_password_message = "Passwords do not match!"
                        else:
                            forgot_password_message = "Please fill out all fields."
                            
                    # Check if the back button is clicked
                    elif pygame.Rect(10, 10, 100, 100).collidepoint(mouse_pos):
                        current_page = "login"
                        signup_username_text = signup_password_text = ''
                        signup_message = ''
                        active_field = None
                
# Handle keyboard input for active fields
        if event.type == pygame.KEYDOWN:
            if active_field == 'username':
                if event.key == pygame.K_BACKSPACE:
                    username_text = username_text[:-1]
                else:
                    username_text += event.unicode
            elif active_field == 'password':
                if event.key == pygame.K_BACKSPACE:
                    password_text = password_text[:-1]
                else:
                    password_text += event.unicode
            elif active_field == 'name':
                if event.key == pygame.K_BACKSPACE:
                    name_text = name_text[:-1]
                else:
                    name_text += event.unicode
            elif active_field == 'signup_username':
                if event.key == pygame.K_BACKSPACE:
                    signup_username_text = signup_username_text[:-1]
                else:
                    signup_username_text += event.unicode
            elif active_field == 'signup_password':
                if event.key == pygame.K_BACKSPACE:
                    signup_password_text = signup_password_text[:-1]
                else:
                    signup_password_text += event.unicode
            elif active_field == 'forgot_password_username':
                if event.key == pygame.K_BACKSPACE:
                    forgot_password_username = forgot_password_username[:-1]
                else:
                    forgot_password_username += event.unicode
            elif active_field == 'forgot_password_new_password':
                if event.key == pygame.K_BACKSPACE:
                    forgot_password_new_password = forgot_password_new_password[:-1]
                else:
                    forgot_password_new_password += event.unicode
            elif active_field == 'forgot_password_confirm_password':
                if event.key == pygame.K_BACKSPACE:
                    forgot_password_confirm_password = forgot_password_confirm_password[:-1]
                else:
                    forgot_password_confirm_password += event.unicode
                    
    # Display the login or sign-up screen based on the current state
    screen.blit(game_background, (0, 0))
    
    if show_menu:
        if menu_selected:
            draw_selected_screen(menu_selected)
        else:
            draw_menu()
    else:

        # Display the regular login screen
        if current_page == "login":
            pygame.display.set_caption("Login")
            screen.blit(login_text, (200, 70))
            screen.blit(username_label, (100, 150))
            screen.blit(password_label, (100, 250))
            screen.blit(guest_text, (950, 70))
            screen.blit(name_label, (850, 150))

            # Handle active input box colors
            if active_field == 'username':
                color_username = color_active
                color_password = color_passive
                color_name = color_passive
            elif active_field == 'password':
                color_username = color_passive
                color_password = color_active
                color_name = color_passive
            elif active_field == 'name':
                color_username = color_passive
                color_password = color_passive
                color_name = color_active
            else:
                color_username = color_passive
                color_password = color_passive
                color_name = color_passive

            # Draw black-filled input boxes
            pygame.draw.rect(screen, color_username, username_input_rect, 0)  # Fill with black
            pygame.draw.rect(screen, color_password, password_input_rect, 0)  # Fill with black
            pygame.draw.rect(screen, color_name, name_input_rect, 0)  # Fill with black

            # Render input text inside the boxes (in white)
            username_surface = font_reg_small.render(username_text, True, (255, 255, 255))
            password_surface = font_reg_small.render('*' * len(password_text), True, (255, 255, 255))
            name_surface = font_reg_small.render(name_text, True, (255, 255, 255))

            # Blit input text to the screen
            screen.blit(username_surface, (username_input_rect.x + 5, username_input_rect.y + 5))
            screen.blit(password_surface, (password_input_rect.x + 5, password_input_rect.y + 5))
            screen.blit(name_surface, (name_input_rect.x + 5, name_input_rect.y + 5))

            # Draw buttons
            pygame.draw.rect(screen, (128, 128, 128), submit_button_rect_1)
            pygame.draw.rect(screen, (128, 128, 128), submit_button_rect_2)
            screen.blit(submit_button_text, (submit_button_rect_1.x + 5, submit_button_rect_1.y + 5))
            screen.blit(submit_button_text, (submit_button_rect_2.x + 5, submit_button_rect_2.y + 5))
        
            # Display the "Sign Up Now!" text without drawing the rectangle
            screen.blit(signup_button_text, (signup_button_rect.x - 100, signup_button_rect.y + 10))

            # Display the "Forgot Password" button
            pygame.draw.rect(screen, (128, 128, 128), forgot_password_button_rect)
            screen.blit(forgot_password_button_text, (forgot_password_button_rect.x + 10, forgot_password_button_rect.y + 10))

            # Display the guest_message if present
            if guest_message:
                guest_message_surface = font_bold_medium.render(guest_message, True, (255, 0, 0))
                screen.blit(guest_message_surface, (900, 510))  # Positioning below the guest submit button

            # Display user login messages on the same screen
            if login_message:
                message_surface = font_bold_medium.render(login_message, True, (255, 0, 0) if "Invalid" in login_message else (0, 255, 0))
                screen.blit(message_surface, (500, 350))
          
        # Display the signup screen 
        if current_page == "signup":
            pygame.display.set_caption("Sign Up")
            screen.blit(back_button_resized, back_button_rect.topleft)
            
            screen.blit(signup_text, (600, 90))
            screen.blit(username_label, (350, 180))
            screen.blit(password_label, (350, 250))
            
            # Adjust color based on active input field for the signup screen
            if active_field == 'signup_username':
                color_username = color_active
                color_password = color_passive
            elif active_field == 'signup_password':
                color_username = color_passive
                color_password = color_active
            else:
                color_username = color_passive
                color_password = color_passive

            pygame.draw.rect(screen, color_username, signup_username_input_rect, 0)  # Fill with black
            pygame.draw.rect(screen, color_password, signup_password_input_rect, 0)  # Fill with black

            signup_username_surface = font_reg_small.render(signup_username_text, True, (255, 255, 255))
            signup_password_surface = font_reg_small.render('*' * len(signup_password_text), True, (255, 255, 255))

            screen.blit(signup_username_surface, (signup_username_input_rect.x + 5, signup_username_input_rect.y + 5))
            screen.blit(signup_password_surface, (signup_password_input_rect.x + 5, signup_password_input_rect.y + 5))

            pygame.draw.rect(screen, (128, 128, 128), signup_submit_button_rect)
            screen.blit(submit_button_text, (signup_submit_button_rect.x + 10, signup_submit_button_rect.y + 10))

            if signup_message:
                message_surface = font_reg_medium.render(signup_message, True, (255, 0, 0) if "Invalid" in signup_message else (0, 255, 0))
                screen.blit(message_surface, (350, 350))

        # Display the forgot password screen
        elif current_page == "forgot_password":
            pygame.display.set_caption("Forgot Password")
            screen.blit(game_background, (0, 0))
            screen.blit(back_button_resized, back_button_rect.topleft)
            screen.blit(forgot_password_label, ((screen_width - forgot_password_label.get_width()) // 2, 90))

            # Change input box color based on which field is active
            color_fp_username = color_active if active_field == 'forgot_password_username' else color_passive
            color_fp_new_password = color_active if active_field == 'forgot_password_new_password' else color_passive
            color_fp_confirm_password = color_active if active_field == 'forgot_password_confirm_password' else color_passive

            pygame.draw.rect(screen, color_fp_username, forgot_password_username_rect, 0)
            pygame.draw.rect(screen, color_fp_new_password, forgot_password_new_password_rect, 0)
            pygame.draw.rect(screen, color_fp_confirm_password, forgot_password_confirm_password_rect, 0)

            # Display labels aligned with input boxes
            screen.blit(fp_username_label, (center_x_position -140, forgot_password_username_rect.y-10))
            screen.blit(fp_new_password_label, (center_x_position-140, forgot_password_new_password_rect.y-10))
            screen.blit(fp_confirm_password_label, (center_x_position-140, forgot_password_confirm_password_rect.y-10))

            # Render input text in white inside the boxes
            forgot_password_username_surface = font_reg_small.render(forgot_password_username, True, (255, 255, 255))
            forgot_password_new_password_surface = font_reg_small.render('*' * len(forgot_password_new_password), True, (255, 255, 255))
            forgot_password_confirm_password_surface = font_reg_small.render('*' * len(forgot_password_confirm_password), True, (255, 255, 255))

            screen.blit(forgot_password_username_surface, (forgot_password_username_rect.x, forgot_password_username_rect.y + 5))
            screen.blit(forgot_password_new_password_surface, (forgot_password_new_password_rect.x + 5, forgot_password_new_password_rect.y + 5))
            screen.blit(forgot_password_confirm_password_surface, (forgot_password_confirm_password_rect.x + 5, forgot_password_confirm_password_rect.y + 5))

            # Draw submit button
            pygame.draw.rect(screen, (128, 128, 128), forgot_password_submit_button_rect)
            screen.blit(submit_button_text, (forgot_password_submit_button_rect.x + 10, forgot_password_submit_button_rect.y + 10))

            if forgot_password_message:
                message_surface = font_reg_medium.render(forgot_password_message, True, (255, 0, 0) if "not" in forgot_password_message else (0, 255, 0))
                screen.blit(message_surface, (400, 380))

    
    pygame.display.flip()
    clock.tick(30)