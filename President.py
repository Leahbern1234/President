import sqlite3
import pygame
import time
import re  # Import the re module for regular expression
from sys import exit

import pygame_menu as pm
import pygame_menu.baseimage 
from pygame_menu.baseimage import BaseImage
pygame.init()

import hashlib

import random

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

# Function to hash a password using SHA-256
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

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
        hashed_password = hash_password(password)
        cursor.execute("INSERT INTO Users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        return "Account created successfully."

# Check if the user exists and password matches
def find_user(username, password):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if user and user['password'] == hash_password(password):
        return user
    return None

# Create a new guest user (if necessary)
def create_guest_user(guest_name):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ?", (guest_name,))
    existing_user = cursor.fetchone()

    if existing_user:
        return "Guest name already exists.\n Please choose a \n different name."
    else:
        cursor.execute("INSERT INTO Users (username, password, guest) VALUES (?, ?, ?)", (guest_name, hash_password("guest_password"), True))
        conn.commit()
        cursor.execute("SELECT user_id FROM Users WHERE username = ?", (guest_name,))
        new_guest_user = cursor.fetchone()
        global user_id
        user_id = new_guest_user["user_id"]
        global show_menu
        show_menu = True
        return f"Guest user {guest_name} \n created successfully."

# Function to update the password for the forgot password feature
def update_password(username, new_password):
    cursor = conn.cursor()
    # Retrieve the current password for the user
    cursor.execute("SELECT password FROM Users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        current_password = existing_user["password"]
        hashed_new_password = hash_password(new_password)
        
        # Check if the new password is the same as the current one
        if current_password == hashed_new_password:
            return "Password is the same as before. Please choose a \n different password."
        
        # Check password length
        if len(new_password) < 8:
            return "Password is too short. It must be at least 8 \n characters long."
        
        # Update the password in the database
        cursor.execute("UPDATE Users SET password = ? WHERE username = ?", (hashed_new_password, username))
        conn.commit()
        return "Password updated successfully. Please log in."
    else:
        return "Username not found."

# Pygame setup
screen = pygame.display.set_mode((1400, 780))
pygame.display.set_caption("President")
clock = pygame.time.Clock()

pygame_icon = pygame.image.load('Images/game_icon.png').convert_alpha()
pygame.display.set_icon(pygame_icon)
# Load images
front_page_image = pygame.image.load("Images/Front_Page.jpg").convert_alpha()
game_background = pygame.image.load("Images/Background.jpg").convert_alpha()
play_background = pygame.image.load("Images/play_background.jpg").convert_alpha()

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
BLUE = (37, 150, 190)

# Variables for game settings
rounds = 5
difficulty_options = [("Easy", "Easy"), ("Medium", "Medium"), ("Hard", "Hard")]
selected_difficulty = difficulty_options[1][1]  # Default to "Medium"
rounds_label = None
game_started = False
hands = None
played_cards = []  # Store played cards
card_deck = []  # Store the shuffled deck
selected_cards = []  # Track selected cards


# Load and resize the play icon using BaseImage
play2_icon_image = BaseImage(image_path='Images/play2.png', drawing_mode=pygame_menu.baseimage.IMAGE_MODE_FILL)
play2_icon_image.scale(0.2, 0.2)  # Scale the image

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
    
# Define a default user_id for guest users
GUEST_USER_ID = -1

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

# List of card names
card_names = [
    '2_of_clubs', '3_of_clubs', '4_of_clubs', '5_of_clubs', '6_of_clubs', '7_of_clubs', '8_of_clubs', '9_of_clubs', '10_of_clubs', 'jack_of_clubs2', 'queen_of_clubs2', 'king_of_clubs2', 'ace_of_clubs',
    '2_of_diamonds', '3_of_diamonds', '4_of_diamonds', '5_of_diamonds', '6_of_diamonds', '7_of_diamonds', '8_of_diamonds', '9_of_diamonds', '10_of_diamonds', 'jack_of_diamonds2', 'queen_of_diamonds2', 'king_of_diamonds2', 'ace_of_diamonds',
    '2_of_hearts', '3_of_hearts', '4_of_hearts', '5_of_hearts', '6_of_hearts', '7_of_hearts', '8_of_hearts', '9_of_hearts', '10_of_hearts', 'jack_of_hearts2', 'queen_of_hearts2', 'king_of_hearts2', 'ace_of_hearts',
    '2_of_spades', '3_of_spades', '4_of_spades', '5_of_spades', '6_of_spades', '7_of_spades', '8_of_spades', '9_of_spades', '10_of_spades', 'jack_of_spades2', 'queen_of_spades2', 'king_of_spades2', 'ace_of_spades2',
    'black_joker', 'red_joker'
]

# Define the new size for the card images
card_size = (100, 140)  # Width, Height

# Load all card images
deck = {}
for card_name in card_names:
    card_image = pygame.image.load(f'Cards_png/{card_name}.png').convert_alpha()
    card_image = pygame.transform.smoothscale(card_image, card_size)  # Resize the card image
    deck[card_name] = card_image

def shuffle_deck():
    shuffled_deck = list(deck.keys())  # Create a list of card names
    random.shuffle(shuffled_deck)  # Shuffle the list in place
    return shuffled_deck

def deal_deck(num_players=5):
    shuffled_deck = shuffle_deck()
    hands = {f'Player {i+1}': [] for i in range(num_players - 1)}
    hands['User'] = []  # Add the User to the hands dictionary
    
    for i, card in enumerate(shuffled_deck):
        player = f'Player {i % (num_players - 1) + 1}' if i % num_players != 0 else 'User'
        hands[player].append(card)
    
    return hands
    
# Global variable for the message
current_message = ""

# Function to set the message
def set_message(message):
    global current_message
    current_message = message

def display_hands(hands):
    screen.blit(game_background, (0, 0))

    y_offset = 50
    for player, cards in hands.items():
        x_offset = 50
        player_text = font_reg_medium.render(player, True, (255, 255, 255))
        screen.blit(player_text, (x_offset, y_offset))
        y_offset += 40
        
        for card in cards:
            card_image = deck[card]
            screen.blit(card_image, (x_offset, y_offset))
            x_offset += card_image.get_width() + 10
        
        y_offset += 20
    
    pygame.display.flip()

# Load the back card image
back_card_image = pygame.image.load('Cards_png/Card_back.png').convert_alpha()
back_card_image = pygame.transform.smoothscale(back_card_image, card_size)  # Resize the back card image

# Rotate the back card image by 90 degrees for players 3 and 4
back_card_image_rotated = pygame.transform.rotate(back_card_image, 90)

# Define card ranks and values
card_order = {
    '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, '10': 8,
    'jack': 9, 'queen': 10, 'king': 11, 'ace': 12, '2': 13, 'joker': 14
}

roles = ['President', 'Vice President', 'Middle', 'Vice Bum', 'Bum']

# Define the number of players
num_players = 5  # Adjust as needed

# Add Jokers to the card names
card_names.extend(['black_joker', 'red_joker'])

def card_sort_key(card):
    rank = card.split('_')[0]
    if 'joker' in card:
        return (15, card)  # Ensure jokers are sorted last
    return (card_order.get(rank, 0), card)

# Define positions and overlap_offset globally
positions = {
    'User': (screen_width // 2 - 200, screen_height - 200),  # Add position for User
    'Player 1': (320, 30), 
    'Player 2': (screen_width - 620, 30),  
    'Player 3': (100, screen_height // 2 - 180),
    'Player 4': (screen_width - 200, screen_height // 2 - 180)
}
overlap_offset = 30

player_order = ['User', 'Player 3', 'Player 1', 'Player 2', 'Player 4']
current_player = None

selected_card = None

# Function to draw the game
def draw_game():
    screen.blit(play_background, (0, 0))
    
    # Sort each player's cards using card_sort_key
    for player, cards in hands.items():
        cards.sort(key=card_sort_key)  # Sort cards before displaying
        
        x_offset, y_offset = positions[player]
        if player != 'User':  
            player_text = font_reg_small.render(player, True, (255, 255, 255))
            screen.blit(player_text, (x_offset, y_offset))
            y_offset += 40
        
        for card in cards:
            if player == 'User':
                card_image = deck[card]
                if card == selected_card:  # Check if this is the selected card
                    screen.blit(card_image, (x_offset, y_offset - 15))  # Raise the card
                else:
                    screen.blit(card_image, (x_offset, y_offset))
                x_offset += overlap_offset  
            elif player in ['Player 3', 'Player 4']:
                card_image = back_card_image_rotated  
                screen.blit(card_image, (x_offset, y_offset))
                y_offset += overlap_offset
            else:
                card_image = back_card_image  
                screen.blit(card_image, (x_offset, y_offset))
                x_offset += overlap_offset  

    # Display played cards stacked on top of each other and moved up slightly
    y_offset = screen_height // 2 - 100  # Move the discard pile up
    x_offset = screen_width // 2 - 50

    # Ensure the 3 of clubs stays at the bottom of the pile if it has been played
    if three_of_clubs_played:
        card_image = deck['3_of_clubs']
        screen.blit(card_image, (x_offset, y_offset))

    for card in played_cards:
        if card != '3_of_clubs':  # Skip the 3 of clubs as it is already drawn
            card_image = deck[card]
            screen.blit(card_image, (x_offset, y_offset))
            
    # Button Logic
    button_rect = pygame.Rect(screen_width // 2 - 60, screen_height - 330, 80, 40)
    if selected_card:
        button_text = font_bold_small.render('Play', True, (255, 255, 255))
    else:
        button_text = font_bold_small.render('Pass', True, (255, 255, 255))
    
    pygame.draw.rect(screen, (128, 128, 128), button_rect)
    text_width, text_height = button_text.get_size()
    text_x = button_rect.x + (button_rect.width - text_width) // 2
    text_y = button_rect.y + (button_rect.height - text_height) // 2
    screen.blit(button_text, (text_x, text_y))

    # Display the current message
    if current_message:
        message_surface = font_reg_small.render(current_message, True, (0, 0, 0))
        screen.blit(message_surface, (screen_width // 2 - message_surface.get_width() // 2, screen_height - 250))
        
    pygame.display.flip()
    
# Function to animate a card to the center of the screen
def animate_card_to_center(card):
    card_image = deck[card]
    x_start, y_start = positions['User']  # Starting position of the card
    x_end, y_end = screen.get_width() // 2 - card_size[0] // 2, screen.get_height() // 2 - card_size[1] // 2 - 100  # Move up slightly

    # Animate the card to the center of the screen
    for i in range(20):  # Number of frames for the animation
        x = x_start + (x_end - x_start) * i / 20
        y = y_start + (y_end - y_start) * i / 20

        # Clear the screen and redraw
        screen.blit(game_background, (0, 0))
        draw_game()
        screen.blit(card_image, (x, y))  
        pygame.display.update()
        pygame.time.wait(50)  # Control animation speed

# Global variable to track the number of consecutive passes
pass_count = 0

# Function to get the next player in the order
def get_next_player(current_player):
    next_player_index = (player_order.index(current_player) + 1) % len(player_order)
    return player_order[next_player_index]

def handle_mouse_click(pos, hands):
    global selected_card, played_cards, current_message, pass_count, current_player
    
    if current_player == 'User':  # Only allow clicking if it's the user's turn
        # Check for button click first
        button_rect = pygame.Rect(screen_width // 2 - 60, screen_height - 330, 80, 40)
        if button_rect.collidepoint(pos):
            if selected_card:  # If a card is selected, this is a "Play" button
                if can_play_card(selected_card):
                    # Play the card
                    animate_card_to_center(selected_card)
                    hands['User'].remove(selected_card)
                    played_cards.append(selected_card)
                    current_message = f"User played {selected_card}!"
                    selected_card = None  # Reset selected card after playing
                    pass_count = 0  # Reset pass count when a card is played
                    if selected_card and ('2' in selected_card or 'joker' in selected_card or len(played_cards) == 4):
                        end_round()
                    return True  # User's turn is complete
                else:
                    current_message = f"Cannot play {selected_card}. It must be of a higher value than the current card."
                    pygame.display.flip()  # Update the display
                    pygame.time.wait(1500)  # Show error message for 1.5 seconds
                selected_card = None  # Reset the selection
            else:  # If no card is selected, this is a "Pass" button
                pass_count += 1
                current_message = "User passed."
                if pass_count >= len(player_order) - 1:
                    played_cards = []  # Clear the played cards if all players pass
                    pass_count = 0
                    end_round()
                return True  # User's turn is complete
            draw_game()  # Redraw to update the display
            return False

        # Handle card selection
        x_offset, y_offset = positions['User']
        card_width, card_height = card_size
        for i, card in enumerate(hands['User']):
            card_rect = pygame.Rect(x_offset, y_offset - (15 if card == selected_card else 0), card_width, card_height)
            if (card_rect.left <= pos[0] <= card_rect.left + overlap_offset or  
                (i == len(hands['User']) - 1 and card_rect.collidepoint(pos))):
                if card == selected_card:
                    selected_card = None  # Lower the card if it's clicked again
                else:
                    selected_card = card  # Raise the new card, lower any previously raised card
                draw_game()  # Redraw to show the new selection
                return False  # User's turn is not complete
            x_offset += overlap_offset

    return False  # User's turn is not complete

def player_with_three_of_clubs(hands):
    for player, cards in hands.items():
        if '3_of_clubs' in cards:
            return player
    return None

# Add a global variable to track if the 3 of clubs has been played
three_of_clubs_played = False

def animate_three_of_clubs_to_center():
    global current_player, player_order, three_of_clubs_played
    card_image = deck['3_of_clubs']
    x_start = positions[current_player][0]  # Current player position
    y_start = positions[current_player][1]  # Current player position
    x_end, y_end = screen.get_width() // 2 - card_size[0] // 2, screen.get_height() // 2 - card_size[1] // 2 - 50  # Move up slightly

    for i in range(20):  # Number of frames for the animation
        x = x_start + (x_end - x_start) * i / 20
        y = y_start + (y_end - y_start) * i / 20

        screen.blit(game_background, (0, 0))
        draw_game()  # Redraw the game state
        screen.blit(card_image, (x, y))  # Render the card in its new position
        pygame.display.update()
        pygame.time.wait(50)  # Control the animation speed

    # Check if the current player has the 3 of clubs before removing it
    if '3_of_clubs' in hands[current_player]:
        hands[current_player].remove('3_of_clubs')
        played_cards.append('3_of_clubs')  # Keep track of played cards
        three_of_clubs_played = True  # Set the flag to indicate the 3 of clubs has been played

    # Set the next player in clockwise order
    current_player = get_next_player(current_player)
    set_message(f"{current_player}'s turn.")
    
def ai_play(player):
    global played_cards, hands, player_order, current_message, pass_count, current_player
    
    # Add a delay for visual clarity
    pygame.time.wait(1000)  

    # Safety check to ensure the correct player is playing
    if player != current_player:
        return False

    card_to_play = None

    # Check if player has any cards left
    if not hands[player]:
        current_message = f"{player} has no cards left."
        return True

    if not played_cards:
        # Start a new round with the lowest card(s)
        card_to_play = min(hands[player], key=card_sort_key)
        hands[player].remove(card_to_play)
        played_cards.append(card_to_play)
        current_message = f"{player} played {card_to_play}."
        pass_count = 0
    else:
        last_played = played_cards[-1]
        valid_cards = [card for card in hands[player] if card_sort_key(card) > card_sort_key(last_played)]
        if valid_cards:
            card_to_play = min(valid_cards, key=card_sort_key)
            hands[player].remove(card_to_play)
            played_cards.append(card_to_play)
            current_message = f"{player} played {card_to_play}."
            pass_count = 0
        else:
            current_message = f"{player} passed."
            pass_count += 1
            if pass_count >= len(player_order) - 1:
                played_cards = []  # Clear the played cards if all players pass
                pass_count = 0

    # Check if the player has won
    if not hands[player]:
        player_roles[player] = len(player_roles) + 1
        player_order.remove(player)
        if len(player_order) == 1:
            player_roles[player_order[0]] = len(player_roles) + 1
            end_round()
            return True

    # Return True to indicate the turn is complete
    return True
    
def start_game():
    global user_id, game_started, hands, current_player, played_cards, player_roles, selected_cards, pass_count
    if 'user_id' not in globals():
        user_id = GUEST_USER_ID
    save_game_preferences(user_id, rounds, selected_difficulty)
    
    hands = deal_deck()
    current_player = player_with_three_of_clubs(hands)
    if current_player:
        animate_three_of_clubs_to_center()

    game_started = True
    played_cards = []
    player_roles = {}
    selected_cards = []
    pass_count = 0
    
    while game_started:
        set_message(f"{current_player}'s turn.")
        pygame.display.set_caption("Game")
        draw_game()
        
        if current_player == 'User':
            turn_completed = False
            while not turn_completed and game_started:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        return
                    
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = pygame.mouse.get_pos()
                        turn_completed = handle_mouse_click(mouse_pos, hands)
                        if turn_completed:
                            current_player = get_next_player(current_player)
                draw_game()
                clock.tick(30)
        else:
            # AI turn
            if ai_play(current_player):
                current_player = get_next_player(current_player)
            draw_game()
            pygame.time.wait(500)  # Add a small delay for visual clarity
        
        
def can_play_card(card):
    if not played_cards:
        return True
    last_played = played_cards[-1]
    if isinstance(last_played, list):
        return card_sort_key(card) >= card_sort_key(last_played[0])  
    return card_sort_key(card) >= card_sort_key(last_played)  
        
def play_card(player, cards):
    global current_player, played_cards, player_order, player_roles, pass_count
    if not played_cards or (len(cards) == len(played_cards[-1]) and card_sort_key(cards[0]) >= card_sort_key(played_cards[-1][0])):
        played_cards.append(cards)
        for card in cards:
            hands[player].remove(card)
        
        # Check if the player has won
        if not hands[player]:
            player_roles[player] = len(player_roles) + 1
            player_order.remove(player)
            if len(player_order) == 1:
                player_roles[player_order[0]] = len(player_roles) + 1
                end_round()
                return True  # Indicate that the game has ended
        
        # Check if a two or a joker is played to end the round
        if '2' in cards[0] or 'joker' in cards[0]:
            end_round()
            return False  # Indicate that the round has ended
        
        # Check if a four of a kind is played to clear the pile
        if len(cards) == 4 and all(card_sort_key(card) == card_sort_key(cards[0]) for card in cards):
            played_cards = []
            set_message(f"{player} cleared the pile with four of a kind!")
            return False  # Indicate that the round has ended

        # Move to the next player
        current_player = get_next_player(current_player)
        set_message(f"{current_player}'s turn.")
    
    return False  # Indicate that the game continues

def end_round():
    global current_player, played_cards, player_order, player_roles
    played_cards = []
    current_player = player_order[0]
    
    if len(player_roles) == num_players:
        assign_roles()
        exchange_cards()
        start_new_round()

def assign_roles():
    global player_roles
    for player, role in zip(sorted(player_roles, key=player_roles.get), roles):
        player_roles[player] = role
    set_message("Roles assigned: " + ", ".join([f"{player}: {role}" for player, role in player_roles.items()]))

def exchange_cards():
    global hands, player_roles
    president = [player for player, role in player_roles.items() if role == 'President'][0]
    bum = [player for player, role in player_roles.items() if role == 'Bum'][0]
    vice_president = [player for player, role in player_roles.items() if role == 'Vice President'][0]
    vice_bum = [player for player, role in player_roles.items() if role == 'Vice Bum'][0]
    
    # President gives their two worst cards to Bum
    worst_cards = sorted(hands[president], key=card_sort_key)[:2]
    hands[president] = hands[president][2:]
    hands[bum].extend(worst_cards)
    
    # Bum gives their two best cards to President
    best_cards = sorted(hands[bum], key=card_sort_key)[-2:]
    hands[bum] = hands[bum][:-2]
    hands[president].extend(best_cards)
    
    # Vice President gives their one worst card to Vice Bum
    worst_card = sorted(hands[vice_president], key=card_sort_key)[0]
    hands[vice_president] = hands[vice_president][1:]
    hands[vice_bum].append(worst_card)
    
    # Vice Bum gives their one best card to Vice President
    best_card = sorted(hands[vice_bum], key=card_sort_key)[-1]
    hands[vice_bum] = hands[vice_bum][:-1]
    hands[vice_president].append(best_card)
    
    set_message(f"{president} gave {worst_cards} to {bum}. {bum} gave {best_cards} to {president}. {vice_president} gave {worst_card} to {vice_bum}. {vice_bum} gave {best_card} to {vice_president}.")
    
def start_new_round():
    global hands, current_player, played_cards, player_order, player_roles
    hands = deal_deck()
    current_player = 'President' if 'Bum' not in player_roles else [player for player, role in player_roles.items() if role == 'Bum'][0]
    played_cards = []
    player_order = ['User', 'Player 3', 'Player 1', 'Player 2', 'Player 4']
    player_roles = {}
    set_message(f"New round started! {current_player}'s turn.")

theme = pm.themes.THEME_DARK.copy()
theme.widget_font = 'Arial'  # Replace with a font supporting Unicode
preferences_menu = pm.Menu(title="Game Preferences", width=700, height=600, theme=theme)

# Rounds selection controls
preferences_menu.add.label("Select Number of Rounds", font_name=font_bold_big)
preferences_menu.add.button('\u25B2', increment_rounds)  # Up button
rounds_label = preferences_menu.add.label(f"{rounds} Rounds", font_name=font_reg_medium)  # Label
preferences_menu.add.button('\u25BC', decrement_rounds)  # Down button

# Add some space before the "Let's Play!" button
preferences_menu.add.vertical_margin(50)

# Create a frame for the play icon and the "Let's Play!" button
play_button_frame = preferences_menu.add.frame_h(300, 60)  # Increase the height of the frame

# Add the "Let's Play!" button and the play icon to the frame
play_button_frame.pack(preferences_menu.add.button("Let's Play!", start_game, font_name=font_bold_medium, font_color=WHITE, 
                                                   background_color=BLUE).set_max_height(40), align=pygame_menu.locals.ALIGN_CENTER)
play_button_frame.pack(preferences_menu.add.image(play2_icon_image).set_max_height(40), 
                       align=pygame_menu.locals.ALIGN_CENTER)

def draw_background():
    screen.blit(game_background, (0, 0))

# Main loop to display the preferences menu
def draw_game_preferences():
    pygame.display.set_caption("Game Preferences")
    preferences_menu.mainloop(screen, bgfun=draw_background)
 
# Main loop
show_menu = False
game_started = False
hands = None  # Initialise hands variable

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
    
        if show_menu:
            check_hover()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                handle_menu_click(mouse_pos)  # Handle clicking on icons and text
                
                # Check if the back button is clicked on the selected screen
                if menu_selected and back_button_rect.collidepoint(mouse_pos):
                    menu_selected = None  # Go back to the main menu
                
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
            continue  # Skip to the next frame (so login screen shows next)
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
                            if guest_message.startswith("Guest user"):
                                show_menu = True  # Trigger to show main menu for guest login
                                pygame.display.set_caption("Main Menu")
                            else:
                                show_menu = False  # Stay on the same screen if name already exists
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
                        
        if game_started:
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if handle_mouse_click(mouse_pos, hands, current_player):  # Pass hands and current_player
                    # Set the next player in clockwise order
                    next_player_index = (player_order.index(current_player) + 1) % len(player_order) 
                    current_player = player_order[next_player_index]
                    set_message(f"{current_player}'s turn.")
            
            while current_player != 'User':
                # ai_play(current_player)
                draw_game()  # Redraw the game state after each AI turn
                pygame.time.wait(1000)  # Add a delay to make AI turns visible
                next_player_index = (player_order.index(current_player) + 1) % len(player_order)
                current_player = player_order[next_player_index]
                set_message(f"{current_player}'s turn.")
                
                
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
    
    if game_started:
        pygame.display.set_caption("Game")
        draw_game()
        continue
    elif show_menu:
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