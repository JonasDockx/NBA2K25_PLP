"""
We define the routes for registration and login.
"""

import random
import json
import string
import requests

from flask import render_template, url_for, flash, redirect, request, session, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from authlib.integrations.flask_client import OAuth
from werkzeug.security import generate_password_hash
from itsdangerous import URLSafeTimedSerializer
from google.oauth2.credentials import Credentials

from app import app, db, bcrypt, mail
from app.models import User, Player, UserSettings, PlayerTargets
from utils.gmail_service import send_email
from utils.scrape_2kratings import scrape_player_data

ATTRIBUTE_LIST = [
    "agility",
    "ball_handle",
    "block",
    "close_shot",
    "defensive_consistency",
    "defensive_rebound",
    "draw_foul",
    "driving_dunk",
    "free_throw",
    "hands",
    "help_defense_iq",
    "hustle",
    "intangibles",
    "interior_defense",
    "layup",
    "mid_range_shot",
    "offensive_consistency",
    "offensive_rebound",
    "overall_durability",
    "pass_accuracy",
    "pass_iq",
    "pass_perception",
    "pass_vision",
    "perimeter_defense",
    "post_control",
    "post_fade",
    "post_hook",
    "shot_iq",
    "speed",
    "speed_with_ball",
    "stamina",
    "standing_dunk",
    "steal",
    "strength",
    "three_point_shot",
    "vertical",
]

BADGE_LIST = [
    "aerial_wizard",
    "ankle_assassin",
    "bail_out",
    "boxout_beast",
    "break_starter",
    "brick_wall",
    "challenger", 
    "deadeye",
    "dimer",
    "float_game",
    "glove",
    "handles_for_days",
    "high_flying_denier",
    "hook_specialist", 
    "immovable_enforcer",
    "interceptor",
    "layup_mixmaster",
    "lightning_launch",
    "limitless_range", 
    "mini_marksman",
    "off_ball_pest",
    "on_ball_menace",
    "paint_patroller",
    "paint_prodigy",
    "pick_dodger", 
    "pogo_stick",
    "posterizer",
    "post_fade_phenom",
    "post_lockdown",
    "post_powerhouse",
    "post_up_poet", 
    "physical_finisher",
    "rebound_chaser",
    "rise_up",
    "set_shot_specialist",
    "shifty_shooter",
    "slippery_off_ball", 
    "strong_handle",
    "unpluckable",
    "versatile_visionary",
]

BADGE_LEVELS = ["None", "Bronze", "Silver", "Gold", "Hall of Fame", "Legendary"]

# Initialize OAuth
oauth = OAuth(app)

# Register Google OAuth
google = oauth.register(
    name="google",
    client_id=app.config["LOGIN_CLIENT_ID"],
    client_secret=app.config["LOGIN_CLIENT_SECRET"],
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    access_token_url="https://accounts.google.com/o/oauth2/token",
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    client_kwargs={"scope": "openid email profile"}
)

def generate_confirmation_token(email):
    """
    Generating a confirmation token.
    """
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    return serializer.dumps(email, salt=app.config["SECURITY_PASSWORD_SALT"])

def confirm_token(token, expiration=3600):
    """
    Confirming the token.
    """
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    try:
        email = serializer.loads(
            token,
            salt=app.config["SECURITY_PASSWORD_SALT"],
            max_age=expiration
        )
    except:
        return False
    return email

@app.route("/register", methods=["GET", "POST"])
def register():
    """
    This is the logic for users registering themselves.
    """
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if not username or not email or not password:
            flash("Please fill out all fields", "danger")
            return render_template("register.html")

        # Check if username or email is already in use
        existing_user = User.query.filter(
            (User.email == email) | (User.username == username)
        ).first()

        if existing_user:
            if existing_user.email == email:
                flash("This e-mail is already registered. Please use another e-mail", "danger")
            if existing_user.username == username:
                flash("This username is already taken. Please choose another.", "danger")
            return redirect(url_for("register"))

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        #Create new user
        user = User(username=username, email=email, password=hashed_password, is_active=True)
        db.session.add(user)
        db.session.commit()

        # # Generate the confirmation token
        # token = generate_confirmation_token(email)
        # confirm_url = url_for("confirm_email", token=token, _external=True)

        # # Email content with the confirmation link
        # email_body = f"Please click the link to confirm your email: {confirm_url}"

        # # Send the confimation email
        # send_email("me", email, "Confirm your e-mail", email_body)

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    This is the logic for customers logging in.
    """
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()

        # Check if user exists and password is correct
        if user and bcrypt.check_password_hash(user.password, password):
            session.permanent = True
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Login Unsuccessful. Please check email and password.", "danger")

    return render_template("login.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    """
    This is the main hub where users can navigate to different features.
    """
    return render_template("dashboard.html")


@app.route("/add_player", methods=["GET", "POST"])
@login_required
def add_player():
    """
    Adding a player to the database.
    """
    if request.method == "POST":
        name = request.form.get("name")
        user_id = current_user.id

        devpoints = int(request.form.get("devpoints", 0))
        badgepoints = int(request.form.get("badgepoints", 0))

        agility = int(request.form.get("agility", 25))
        ball_handle = int(request.form.get("ball_handle", 25))
        block = int(request.form.get("block", 25))
        close_shot = int(request.form.get("close_shot", 25))
        defensive_consistency = int(request.form.get("defensive_consistency", 25))
        defensive_rebound = int(request.form.get("defensive_rebound", 25))
        draw_foul = int(request.form.get("draw_foul", 25))
        driving_dunk = int(request.form.get("driving_dunk", 25))
        free_throw = int(request.form.get("free_throw", 25))
        hands = int(request.form.get("hands", 25))
        help_defense_iq = int(request.form.get("help_defense_iq", 25))
        hustle = int(request.form.get("hustle", 25))
        intangibles = int(request.form.get("intangibles", 25))
        interior_defense = int(request.form.get("interior_defense", 25))
        layup = int(request.form.get("layup", 25))
        mid_range_shot = int(request.form.get("mid_range_shot", 25))
        offensive_consistency = int(request.form.get("offensive_consistency", 25))
        offensive_rebound = int(request.form.get("offensive_rebound", 25))
        overall_durability = int(request.form.get("overall_durability", 25))
        pass_accuracy = int(request.form.get("pass_accuracy", 25))
        pass_iq = int(request.form.get("pass_iq", 25))
        pass_perception = int(request.form.get("pass_perception", 25))
        pass_vision = int(request.form.get("pass_vision", 25))
        perimeter_defense = int(request.form.get("perimeter_defense", 25))
        post_control = int(request.form.get("post_control", 25))
        post_fade = int(request.form.get("post_fade", 25))
        post_hook = int(request.form.get("post_hook", 25))
        shot_iq = int(request.form.get("shot_iq", 25))
        standing_dunk = int(request.form.get("standing_dunk", 25))
        speed = int(request.form.get("speed", 25))
        speed_with_ball = int(request.form.get("speed_with_ball", 25))
        stamina = int(request.form.get("stamina", 25))
        steal = int(request.form.get("steal", 25))
        strength = int(request.form.get("strength", 25))
        three_point_shot = int(request.form.get("three_point_shot", 25))
        vertical = int(request.form.get("vertical", 25))

        aerial_wizard = request.form.get("aerial_wizard", "None")
        ankle_assassin = request.form.get("ankle_assassin", "None")
        bail_out = request.form.get("bail_out", "None")
        boxout_beast = request.form.get("boxout_beast", "None")
        break_starter = request.form.get("break_starter", "None")
        brick_wall = request.form.get("brick_wall", "None")
        challenger = request.form.get("challenger", "None")
        deadeye = request.form.get("deadeye", "None")
        dimer = request.form.get("dimer", "None")
        float_game = request.form.get("float_game", "None")
        glove = request.form.get("glove", "None")
        handles_for_days = request.form.get("handles_for_days", "None")
        high_flying_denier = request.form.get("high_flying_denier", "None")
        hook_specialist = request.form.get("hook_specialist", "None")
        immovable_enforcer = request.form.get("immovable_enforcer", "None")
        interceptor = request.form.get("interceptor", "None")
        layup_mixmaster = request.form.get("layup_mixmaster", "None")
        lightning_launch = request.form.get("lightning_launch", "None")
        limitless_range = request.form.get("limitless_range", "None")
        mini_marksman = request.form.get("mini_marksman", "None")
        off_ball_pest = request.form.get("off_ball_pest", "None")
        on_ball_menace = request.form.get("on_ball_menace", "None")
        paint_patroller = request.form.get("paint_patroller", "None")
        paint_prodigy = request.form.get("paint_prodigy", "None")
        pick_dodger = request.form.get("pick_dodger", "None")
        pogo_stick = request.form.get("pogo_stick", "None")
        posterizer = request.form.get("posterizer", "None")
        post_fade_phenom = request.form.get("post_fade_phenom", "None")
        post_lockdown = request.form.get("post_lockdown", "None")
        post_powerhouse = request.form.get("post_powerhouse", "None")
        post_up_poet = request.form.get("post_up_poet", "None")
        physical_finisher = request.form.get("physical_finisher", "None")
        rebound_chaser = request.form.get("rebound_chaser", "None")
        rise_up = request.form.get("rise_up", "None")
        set_shot_specialist = request.form.get("set_shot_specialist", "None")
        shifty_shooter = request.form.get("shifty_shooter", "None")
        slippery_off_ball = request.form.get("slippery_off_ball", "None")
        strong_handle = request.form.get("strong_handle", "None")
        unpluckable = request.form.get("unpluckable", "None")
        versatile_visionary = request.form.get("versatile_visionary", "None")

        new_player = Player(
            name=name,
            user_id=user_id,
            devpoints=devpoints,
            badgepoints=badgepoints,
            agility=agility,
            ball_handle=ball_handle,
            block=block,
            close_shot=close_shot,
            defensive_consistency=defensive_consistency,
            defensive_rebound=defensive_rebound,
            draw_foul=draw_foul,
            driving_dunk=driving_dunk,
            free_throw=free_throw,
            hands=hands,
            help_defense_iq=help_defense_iq,
            hustle=hustle,
            intangibles=intangibles,
            interior_defense=interior_defense,
            layup=layup,
            mid_range_shot=mid_range_shot,
            offensive_consistency=offensive_consistency,
            offensive_rebound=offensive_rebound,
            overall_durability=overall_durability,
            pass_accuracy=pass_accuracy,
            pass_iq=pass_iq,
            pass_perception=pass_perception,
            pass_vision=pass_vision,
            perimeter_defense=perimeter_defense,
            post_control=post_control,
            post_fade=post_fade,
            post_hook=post_hook,
            shot_iq=shot_iq,
            standing_dunk=standing_dunk,
            speed=speed,
            speed_with_ball=speed_with_ball,
            stamina=stamina,
            steal=steal,
            strength=strength,
            three_point_shot=three_point_shot,
            vertical=vertical,
            aerial_wizard=aerial_wizard,
            ankle_assassin=ankle_assassin,
            bail_out=bail_out,
            boxout_beast=boxout_beast,
            break_starter=break_starter,
            brick_wall=brick_wall,
            challenger=challenger,
            deadeye=deadeye,
            dimer=dimer,
            float_game=float_game,
            glove=glove,
            handles_for_days=handles_for_days,
            high_flying_denier=high_flying_denier,
            hook_specialist=hook_specialist,
            immovable_enforcer=immovable_enforcer,
            interceptor=interceptor,
            layup_mixmaster=layup_mixmaster,
            lightning_launch=lightning_launch,
            limitless_range=limitless_range,
            mini_marksman=mini_marksman,
            off_ball_pest=off_ball_pest,
            on_ball_menace=on_ball_menace,
            paint_patroller=paint_patroller,
            paint_prodigy=paint_prodigy,
            pick_dodger=pick_dodger,
            pogo_stick=pogo_stick,
            posterizer=posterizer,
            post_fade_phenom=post_fade_phenom,
            post_lockdown=post_lockdown,
            post_powerhouse=post_powerhouse,
            post_up_poet=post_up_poet,
            physical_finisher=physical_finisher,
            rebound_chaser=rebound_chaser,
            rise_up=rise_up,
            set_shot_specialist=set_shot_specialist,
            shifty_shooter=shifty_shooter,
            slippery_off_ball=slippery_off_ball,
            strong_handle=strong_handle,
            unpluckable=unpluckable,
            versatile_visionary=versatile_visionary
        )

        db.session.add(new_player)
        db.session.commit()

        flash("Player added successfully!", "success")
        return redirect(url_for("add_player"))
    # Render the form when accessed via GET request
    return render_template("add_player.html")

@app.route("/input_stats", methods=["GET", "POST"])
@login_required
def input_stats():
    """
    Inputting the game statistics.
    """
    if request.method == "POST":
        # Fetch the player
        player_id = request.form.get("player_id")
        player = Player.query.get(player_id)

        # Fetch user-specific settings
        settings = current_user.settings or create_default_settings(current_user)

        # Get game stats from the form
        points = int(request.form.get("points", 0))
        rebounds = int(request.form.get("rebounds", 0))
        assists = int(request.form.get("assists", 0))
        steals = int(request.form.get("steals", 0))
        blocks = int(request.form.get("blocks", 0))

        # Check for additional awards
        player_of_the_game = "player_of_the_game" in request.form
        player_of_the_week = "player_of_the_week" in request.form
        player_of_the_month = "player_of_the_month" in request.form
        roty = "roty" in request.form
        dpoy = "dpoy" in request.form
        mvp = "mvp" in request.form
        champion = "champion" in request.form

        # Calculate development and badge points
        devpoints_earned = 0
        badgepoints_earned = 0

        # Initialize a list to track stats for double doubles and triple doubles
        double_double_stats = [
            points >= 10,
            rebounds >= 10,
            assists >= 10,
            steals >= 10,
            blocks >= 10,
        ]

        # Rebounds and assists points
        if sum(double_double_stats) <= 1:
            if rebounds >= 10 and rebounds < 20:
                devpoints_earned += settings.rebounds_10
            if assists >= 10 and assists < 20:
                devpoints_earned += settings.assists_10
            if points >= 10 and points < 20:
                devpoints_earned += settings.points_10

        # Scoring points
        if points >= 70:
            devpoints_earned += settings.points_70
        elif points >= 60:
            devpoints_earned += settings.points_60
        elif points >= 50:
            devpoints_earned += settings.points_50
        elif points >= 40:
            devpoints_earned += settings.points_40
        elif points >= 30:
            devpoints_earned += settings.points_30
        elif points >= 20:
            devpoints_earned += settings.points_20

        if assists >= 20:
            devpoints_earned += settings.assists_20

        if rebounds >= 20:
            devpoints_earned += settings.rebounds_20

        # double double and triple double points
        double_double_count = sum(double_double_stats)
        if double_double_count == 2:
            devpoints_earned += settings.double_double_2
        elif double_double_count == 3:
            devpoints_earned += settings.double_double_3
        elif double_double_count == 4:
            devpoints_earned += settings.double_double_4
        elif double_double_count == 5:
            devpoints_earned += settings.double_double_5

        # Steals and blocks points
        if steals >= 10:
            devpoints_earned += settings.steals_10
        elif steals >= 6:
            devpoints_earned += settings.steals_6
        elif steals >= 3:
            devpoints_earned += settings.steals_3
        if blocks >= 10:
            devpoints_earned += settings.blocks_10
        elif blocks >= 6:
            devpoints_earned += settings.blocks_6
        elif blocks >= 3:
            devpoints_earned += settings.blocks_3

        # Player of the game/week/month points
        devpoints_earned += int(player_of_the_game) * settings.player_of_the_game
        devpoints_earned += int(player_of_the_week) * settings.player_of_the_week
        devpoints_earned += int(player_of_the_month) * settings.player_of_the_month

        # ROTY, DPOY, MVP and Champion points and badges
        if roty:
            devpoints_earned += settings.roty_points
            badgepoints_earned += settings.roty_badge
        if dpoy:
            devpoints_earned += settings.dpoy_points
            badgepoints_earned += settings.dpoy_badge
        if mvp:
            devpoints_earned += settings.mvp_points
            badgepoints_earned += settings.mvp_badge
        if champion:
            devpoints_earned += settings.champion_points
            badgepoints_earned += settings.champion_badge

        # Update player's points
        player.devpoints += devpoints_earned
        player.badgepoints += badgepoints_earned

        db.session.commit()

        flash(
            f"Success! {devpoints_earned} development points and {badgepoints_earned} badge points awarded.",
            "success"
        )
        return redirect(url_for("input_stats"))
    # Render form if get request
    players = Player.query.filter_by(user_id=current_user.id).all()
    return render_template("input_stats.html", players=players)


@app.route("/upgrade_attribute", methods=["GET", "POST"])
@login_required
def upgrade_attribute():
    """
    The logic for upgrading the attributes.
    """

    attribute_list = ATTRIBUTE_LIST

    badge_list = BADGE_LIST

    badge_levels = BADGE_LEVELS

    player = None
    target_values = {}
    target_badges = {}

    if request.method == "POST":
        # Fetch the player
        player_id = request.form.get("player_id")

        if player_id:
            player = Player.query.get(player_id)

            if player:
                targets = PlayerTargets.query.filter_by(player_id=player.id).first()

                if targets:
                    target_values = {attr: getattr(targets, attr, 99) for attr in attribute_list}
                    target_badges = {badge: getattr(targets, badge, "Legendary") for badge in badge_list}
                else:
                    target_values = {attr: 99 for attr in attribute_list}
                    target_badges = {badge: "Legendary" for badge in badge_list}

            # Get the attribute to upgrade and its current value
            attribute = request.form.get("attribute")
            if attribute and player:
                current_value = getattr(player, attribute)

                # Check if the attribute is at the maximum value
                if current_value >= 99:
                    formatted_name = format_attribute_name(attribute)
                    flash(f"{formatted_name} is already at the maximum value!", "info")
                    return redirect(url_for("upgrade_attribute", player_id=player_id))

                # Define upgrade cost based on the current value
                if current_value < 70:
                    cost = 1
                elif current_value < 80:
                    cost = 2
                elif current_value < 90:
                    cost = 3
                else:
                    cost = 5

                # Check if player has enough development points
                if player.devpoints >= cost:
                    # Deduct development points and increase the attribute
                    player.devpoints -= cost
                    setattr(player, attribute, current_value + 1)

                    db.session.commit()
                    formatted_name = format_attribute_name(attribute)
                    flash(
                        f"Success! {formatted_name} upgraded to {current_value + 1}. {cost} devpoints used.",
                        "success"
                    )
                else:
                    flash("Not enough development points to upgrade this attribute.", "danger")

            # Handle badge upgrades with devpoints
            badge_devpoints = request.form.get("badge_devpoints")
            if badge_devpoints and player:
                current_badge = getattr(player, badge_devpoints)

                # Prevent upgrade if badge is at "Legendary"
                if current_badge == "Legendary":
                    flash(f"{badge_devpoints} is already at the maximum level.", "info")
                    return redirect(url_for("upgrade_attribute", player_id=player_id))

                badge_cost = 0

                # Define badge upgrade cost based on the current badge level
                if current_badge == "None":
                    badge_cost = 3
                elif current_badge == "Bronze":
                    badge_cost = 5
                elif current_badge == "Silver":
                    badge_cost = 7
                elif current_badge == "Gold":
                    badge_cost = 10
                elif current_badge == "Hall of Fame":
                    badge_cost = 20

                if player.devpoints >= badge_cost:
                    player.devpoints -= badge_cost
                    next_badge = get_next_badge_level(current_badge)
                    setattr(player, badge_devpoints, next_badge)

                    db.session.commit()
                    formatted_badge_name = format_attribute_name(badge_devpoints)
                    flash(
                        f"Success! {formatted_badge_name} upgraded to {next_badge}. {badge_cost} devpoints used.",
                        "success"
                    )
                else:
                    flash("Not enough development points to upgrade this badge.", "danger",)

            # Handle badge upgrades with badge points
            badge_badgepoints = request.form.get("badge_badgepoints")
            if badge_badgepoints and player:
                if player.badgepoints > 0:
                    current_badge = getattr(player, badge_badgepoints)
                    next_badge = get_next_badge_level(current_badge)
                    setattr(player, badge_badgepoints, next_badge)
                    player.badgepoints -= 1
                    db.session.commit()
                    formatted_badge_name = format_attribute_name(badge_badgepoints)
                    flash(
                        f"Success! {formatted_badge_name} upgraded to {next_badge} with 1 badge point.",
                        "success"
                    )
                else:
                    flash("Not enough points to upgrade this badge.", "danger")

        return redirect(url_for("upgrade_attribute", player_id=player_id))

    # Handle GET request: display the player and attributes
    player = None
    if "player_id" in request.args:
        player_id = request.args.get("player_id")
        player = Player.query.get(player_id)

        if player:
            targets = PlayerTargets.query.filter_by(player_id=player_id).first()
            if targets:
                target_values = {attr: getattr(targets, attr, 99) for attr in attribute_list}
                target_badges = {badge: getattr(targets, badge, "Legendary") for badge in badge_list}

    # Fetch only the players created by the logged-in user
    players = Player.query.filter_by(user_id=current_user.id).all()

    return render_template(
        "upgrade_attribute.html", 
        players=players,
        player=player,
        target_values=target_values,
        target_badges=target_badges,
        attribute_list=attribute_list,
        badge_list=badge_list,
        badge_levels=badge_levels,
    )

# Helper function to determine next badge level
def get_next_badge_level(current_badge):
    """
    Helper function to determine next badge level.
    """
    badge_levels = ["None", "Bronze", "Silver", "Gold", "Hall of Fame", "Legendary"]
    if current_badge in badge_levels:
        next_level_index = badge_levels.index(current_badge) + 1
        if next_level_index < len(badge_levels):
            return badge_levels[next_level_index]
    return current_badge

@app.route("/")
def home():
    """
    This will render the home page when users go to the root URL.
    """
    return render_template("home.html")

@app.route("/login/google")
def google_login():
    """
    Initiates Google login. This route is for user authentication only.
    No offline access or gmail.send scope here.
    """
    nonce = "".join(random.choices(string.ascii_letters + string.digits, k=16))
    session["nonce"] = nonce
    redirect_uri = app.config["LOGIN_REDIRECT_URI"]
    return google.authorize_redirect(redirect_uri, nonce=nonce)

@app.route("/login/callback")
def google_authorize():
    """
    Handling the Google authorisation callback for user login.
    Note: We do NOT request gmail.send scope or store token.json here.
    This is strictly for authenticating the user.
    """
    token = google.authorize_access_token()
    nonce = session.get("nonce")
    user_info = google.parse_id_token(token, nonce=nonce)
    user_email = user_info["email"]
    name = user_info.get("name", "")

    # Check if user already exists in the database
    user = User.query.filter_by(email=user_email).first()

    if not user:
        new_user = User(
            username=name if name else user_email.split("@")[0],
            email=user_email,
            password=None,
            is_active=True,
        )
        db.session.add(new_user)
        db.session.commit()
        user = new_user

    # Log the user in
    login_user(user)
    return redirect(url_for("dashboard"))

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """
    The logic for the profile page.
    """
    if request.method == "POST":
        # Get the new password from the form
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # Validate the password and update it
        if new_password == confirm_password:
            hashed_password = generate_password_hash(new_password)
            current_user.password = hashed_password
            db.session.commit()
            flash(
                "Your password has been updated!",
                "success"
            )
        else:
            flash(
                "Passwords do not match. Please try again.",
                "danger"
            )

        return redirect(url_for("profile"))

    # Render the profile page
    return render_template("profile.html", user=current_user)

@app.route("/confirm/<token>")
def confirm_email(token):
    """Logic for confirming the e-mail address."""
    try:
        email = confirm_token(token)
    except:
        flash("The confirmation link is invalid or has expired.", "danger")
        return redirect(url_for("login"))

    user = User.query.filter_by(email=email).first_or_404()

    if user.is_active:
        flash("Account already confirmed. Please login.", "success")
    else:
        user.is_active = True
        db.session.commit()
        flash("Your account has been confirmed!", "success")

    return redirect(url_for("login"))

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    """Resetting the user's password."""
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if user:
            token = generate_confirmation_token(user.email)
            reset_url = url_for("reset_password", token=token, _external=True)

            send_email(
                "me", 
                user.email, 
                "Reset Your Password", 
                f"Click the link to reset your password: {reset_url}"
            )

            flash("A password reset link has been sent to your e-mail.", "info")
        else:
            flash("Email not found.", "danger")

    return render_template("forgot_password.html")

@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Resetting the user's password."""
    try:
        email = confirm_token(token)
    except:
        flash("The password reset link is invalid or has expired.", "danger")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("reset_password", token=token))

        # Hash the new password and update the user
        user = User.query.filter_by(email=email).first()
        user.password = bcrypt.generate_password_hash(password).decode("utf-8")
        db.session.commit()

        flash("Your password has been updated!", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", token=token)

@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    """Deleting the customer's account."""
    # Fetch the current user
    user = User.query.get(current_user.id)

    if user:
        if user.settings:
            db.session.delete(user.settings)
        # Delete the user from the database
        db.session.delete(user)
        db.session.commit()

        # Log the user out
        logout_user()

        flash("Your account and all related date have been deleted.", "info")
        return redirect(url_for("home"))
    else:
        flash("Account not found.", "danger")
        return redirect(url_for("profile"))

@app.route("/delete_player/<int:player_id>", methods=["POST"])
@login_required
def delete_player(player_id):
    """
    Route for deleting a player. Only the user whe created the player can delete it.
    """
    player = Player.query.get_or_404(player_id)

    # Ensure that the logged-in user is the owner of the player
    if player.user_id != current_user.id:
        flash("You do not have permission to delete this player.", "danger")
        return redirect(url_for("dashboard"))

    # Delete the player
    db.session.delete(player)
    db.session.commit()
    flash("Player has been deleted.", "success")
    return redirect(url_for("dashboard"))

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    """
    Logs the user out and redirects to the login page.
    """
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """
    Render the main settings page with options to navigate to point system and target settings.
    """
    return render_template("settings.html")

@app.route("/target_settings", methods=["GET", "POST"])
@login_required
def target_settings():
    """
    Handle target value settings for players.
    """
    players = Player.query.filter_by(user_id=current_user.id).all()
    selected_player = None
    target_values = {}
    target_badges = {}
    attribute_list = ATTRIBUTE_LIST
    badge_list = BADGE_LIST

    if request.method == "POST":
        player_id = request.form.get("player_id")
        if player_id:
            selected_player = Player.query.get(player_id)

            targets = PlayerTargets.query.filter_by(player_id=player_id).first()

            if targets:
                target_values = {attr: getattr(targets, attr, 99) for attr in attribute_list}
                target_badges = {badge: getattr(targets, badge, "Legendary") for badge in badge_list}
            else:
                target_values = {attr: 99 for attr in attribute_list}
                target_badges = {badge: "Legendary" for badge in badge_list}

            if "scrape_player" in request.form:
                player_url_part = request.form.get("player_url_part")
                if player_url_part:
                    scraped_data = scrape_player_data(player_url_part)
                    if "error" not in scraped_data:
                        target_values.update(scraped_data.get("attributes", target_values))
                        # target_badges.update(scraped_data.get("badges", target_badges))
                        for badge in badge_list:
                            target_badges[badge] = scraped_data.get("badges", {}).get(badge, "None")
                        flash("Player data scraped successfully!", "success")
                    else:
                        flash(scraped_data["error"], "danger")
            elif "save_targets" in request.form and selected_player:
                targets = PlayerTargets.query.filter_by(player_id=selected_player.id).first()

                if not targets:
                    targets = PlayerTargets(player_id=selected_player.id)
                    db.session.add(targets)
                for attr in attribute_list:
                    setattr(targets, attr, int(request.form.get(f"target_{attr}", 99)))

                for badge in badge_list:
                    setattr(targets, badge, request.form.get(f"target_{badge}", "Legendary"))

                if not targets:
                    targets = PlayerTargets(player_id=player_id)
                    db.session.add(targets)

                db.session.commit()
                flash("Target values saved successfully!", "success")

                return redirect(url_for('target_settings', player_id=selected_player.id))

    return render_template(
        "target_settings.html",
        players=players,
        selected_player=selected_player,
        target_values=target_values,
        target_badges=target_badges,
        attribute_list=attribute_list,
        badge_list=badge_list,
        getattr=getattr
    )

@app.route("/point_system", methods=["GET", "POST"])
@login_required
def point_system():
    """
    Handle settings for point allocation.
    """
    user_settings = current_user.settings or create_default_settings(current_user)

    if request.method == "POST":
        if "revert_default" in request.form:
            reset_to_defaults(user_settings)
            flash("Settings have been reverted to default.", "success")
        elif "save_points" in request.form:
            # Update the settings with form values
            user_settings.points_70 = request.form['points_70']
            user_settings.points_60 = request.form['points_60']
            user_settings.points_50 = request.form['points_50']
            user_settings.points_40 = request.form['points_40']
            user_settings.points_30 = request.form['points_30']
            user_settings.points_20 = request.form['points_20']
            user_settings.points_10 = request.form['points_10']

            user_settings.rebounds_20 = request.form['rebounds_20']
            user_settings.rebounds_10 = request.form['rebounds_10']

            user_settings.assists_20 = request.form['assists_20']
            user_settings.assists_10 = request.form['assists_10']

            user_settings.steals_10 = request.form['steals_10']
            user_settings.steals_6 = request.form['steals_6']
            user_settings.steals_3 = request.form['steals_3']

            user_settings.blocks_10 = request.form['blocks_10']
            user_settings.blocks_6 = request.form['blocks_6']
            user_settings.blocks_3 = request.form['blocks_3']

            user_settings.double_double_2 = request.form['double_double_2']
            user_settings.double_double_3 = request.form['double_double_3']
            user_settings.double_double_4 = request.form['double_double_4']
            user_settings.double_double_5 = request.form['double_double_5']

            user_settings.player_of_the_game = request.form['player_of_the_game']
            user_settings.player_of_the_week = request.form['player_of_the_week']
            user_settings.player_of_the_month = request.form['player_of_the_month']

            user_settings.roty_points = request.form['roty_points']
            user_settings.roty_badge = request.form['roty_badge']
            user_settings.dpoy_points = request.form['dpoy_points']
            user_settings.dpoy_badge = request.form['dpoy_badge']
            user_settings.mvp_points = request.form['mvp_points']
            user_settings.mvp_badge = request.form['mvp_badge']
            user_settings.champion_points = request.form['champion_points']
            user_settings.champion_badge = request.form['champion_badge']

            db.session.commit()
            flash("Settings have been saved.", "success")

    return render_template(
        "point_system.html",
        settings=user_settings,
        default_settings=get_default_settings(),
        )

def create_default_settings(user):
    """Create default settings for the new user"""
    default_settings = get_default_settings()
    new_settings = UserSettings(
        user_id=user.id,
        points_70=default_settings['points_70'],
        points_60=default_settings['points_60'],
        points_50=default_settings['points_50'],
        points_40=default_settings['points_40'],
        points_30=default_settings['points_30'],
        points_20=default_settings['points_20'],
        points_10=default_settings['points_10'],

        rebounds_20=default_settings['rebounds_20'],
        rebounds_10=default_settings['rebounds_10'],

        assists_20=default_settings['assists_20'],
        assists_10=default_settings['assists_10'],

        steals_10=default_settings['steals_10'],
        steals_6=default_settings['steals_6'],
        steals_3=default_settings['steals_3'],

        blocks_10=default_settings['blocks_10'],
        blocks_6=default_settings['blocks_6'],
        blocks_3=default_settings['blocks_3'],

        double_double_2=default_settings['double_double_2'],
        double_double_3=default_settings['double_double_3'],
        double_double_4=default_settings['double_double_4'],
        double_double_5=default_settings['double_double_5'],

        player_of_the_game=default_settings['player_of_the_game'],
        player_of_the_week=default_settings['player_of_the_week'],
        player_of_the_month=default_settings['player_of_the_month'],

        roty_points=default_settings['roty_points'],
        roty_badge=default_settings['roty_badge'],
        dpoy_points=default_settings['dpoy_points'],
        dpoy_badge=default_settings['dpoy_badge'],
        mvp_points=default_settings['mvp_points'],
        mvp_badge=default_settings['mvp_badge'],
        champion_points=default_settings['champion_points'],
        champion_badge=default_settings['champion_badge'],
    )
    db.session.add(new_settings)
    db.session.commit()
    return new_settings

def reset_to_defaults(user_settings):
    """Fetch the default settings"""
    default_settings = get_default_settings()

    # Reset all settings to default
    user_settings.points_70 = default_settings['points_70']
    user_settings.points_60 = default_settings['points_60']
    user_settings.points_50 = default_settings['points_50']
    user_settings.points_40 = default_settings['points_40']
    user_settings.points_30 = default_settings['points_30']
    user_settings.points_20 = default_settings['points_20']
    user_settings.points_10 = default_settings['points_10']

    user_settings.rebounds_20 = default_settings['rebounds_20']
    user_settings.rebounds_10 = default_settings['rebounds_10']

    user_settings.assists_20 = default_settings['assists_20']
    user_settings.assists_10 = default_settings['assists_10']

    user_settings.steals_10 = default_settings['steals_10']
    user_settings.steals_6 = default_settings['steals_6']
    user_settings.steals_3 = default_settings['steals_3']

    user_settings.blocks_10 = default_settings['blocks_10']
    user_settings.blocks_6 = default_settings['blocks_6']
    user_settings.blocks_3 = default_settings['blocks_3']

    user_settings.double_double_2 = default_settings['double_double_2']
    user_settings.double_double_3 = default_settings['double_double_3']
    user_settings.double_double_4 = default_settings['double_double_4']
    user_settings.double_double_5 = default_settings['double_double_5']

    user_settings.player_of_the_game = default_settings['player_of_the_game']
    user_settings.player_of_the_week = default_settings['player_of_the_week']
    user_settings.player_of_the_month = default_settings['player_of_the_month']

    user_settings.roty_points = default_settings['roty_points']
    user_settings.roty_badge = default_settings['roty_badge']
    user_settings.dpoy_points = default_settings['dpoy_points']
    user_settings.dpoy_badge = default_settings['dpoy_badge']
    user_settings.mvp_points = default_settings['mvp_points']
    user_settings.mvp_badge = default_settings['mvp_badge']
    user_settings.champion_points = default_settings['champion_points']
    user_settings.champion_badge = default_settings['champion_badge']

    # Commit the changes to the database
    db.session.commit()

def get_default_settings():
    """Default values for the point system"""
    return {
        'points_70': 20,
        'points_60': 15,
        'points_50': 10,
        'points_40': 5,
        'points_30': 3,
        'points_20': 2,
        'points_10': 1,

        'rebounds_20': 3,
        'rebounds_10': 1,

        'assists_20': 3,
        'assists_10': 1,

        'steals_10': 5,
        'steals_6': 3,
        'steals_3': 1,

        'blocks_10': 5,
        'blocks_6': 3,
        'blocks_3': 1,

        'double_double_2': 3,
        'double_double_3': 5,
        'double_double_4': 15,
        'double_double_5': 30,

        'player_of_the_game': 1,
        'player_of_the_week': 3,
        'player_of_the_month': 5,

        'roty_points': 7,
        'roty_badge': 3,
        'dpoy_points': 5,
        'dpoy_badge': 3,
        'mvp_points': 15,
        'mvp_badge': 3,
        'champion_points': 10,
        'champion_badge': 2,
    }

@app.route("/about")
def about():
    """
    Generating the about page.
    """
    return render_template("about.html")

@app.route("/cookies")
def cookies():
    """
    Generating the cookies page.
    """
    return render_template("cookies.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    """
    Creating the contact page.
    """
    if request.method =="POST":
        name = request.form["name"]
        email = request.form["email"]
        message = request.form["message"]

        if not name or not email or not message:
            flash("All fields are required.", "danger")
            return redirect(url_for("about"))

        # Create the e-mail content
        subject = f"Contact Form Submission from {name}"
        message_text = f"Message from {name} ({email}):\n\n{message}"

        try:
            # Use the send_email function to send the message
            send_email(user_id="me", recipient=app.config["MAIL_DEFAULT_RECIPIENT"], subject=subject, message_text=message_text)
            flash("Your message has been sent. We will get back to you shortly.", "success")
        except Exception as e:
            flash(f"Failed to send message: {str(e)}", "danger")

        return redirect(url_for("about"))

    return render_template("about.html")

@app.route("/scrape_player", methods=["POST"])
def scrape_player():
    """Scraping the player data from 2kratings.com"""
    try:
        player_url_part = request.json.get("player_url_part")
        if not player_url_part:
            return jsonify({"success": False, "error": "Invalid player URL part."})

        player_data = scrape_player_data(player_url_part)

        if not player_data or "error" in player_data:
            error_message = player_data.get("error", "Unable to retrieve player data. Please check the player URL part.")
            return jsonify({"success": False, "error": error_message}), 404

        return jsonify({"success": True, "player_data": player_data})
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "error": "Network error occurred while fetching player data."}), 500
    except Exception as e:
        return jsonify({"success": False, "error": "An unexpected error occurred."}), 500

@app.route("/manual")
def manual():
    """
    Render the manual page.
    """
    return render_template("manual.html")

def format_attribute_name(attribute):
    """Converts snake_case attribute names to Title Case with spaces."""
    return attribute.replace('_', ' ').title()

@app.route("/edit_player", methods=["GET", "POST"])
@login_required
def edit_player():
    """
    Allows the user to edit a player's name, attributes and badges in case
    of an error at player creation.
    """
    attribute_list = ATTRIBUTE_LIST
    badge_list = BADGE_LIST
    players = Player.query.filter_by(user_id=current_user.id).all()

    if request.method == "POST":
        player = Player.query.get_or_404(request.form.get("player_id"))

        # Authorisation (load+save both go through here)
        if player.user_id != current_user.id:
            flash("You do not have permission to edit this player.", "danger")
            return redirect(url_for("dashboard"))

        # Validate everything before writing anything
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Player name cannot be empty.", "danger")
            return redirect(url_for("edit_player", player_id=player.id))

        new_attrs = {}
        for attr in attribute_list:
            raw = request.form.get(attr)
            try:
                val = int(raw)
            except (TypeError, ValueError):
                flash(f"{format_attribute_name(attr)} must be a number.", "danger")
                return redirect(url_for("edit_player", player_id=player.id))
            if val < 25 or val > 99:
                flash(f"{format_attribute_name(attr)} must be between 25 and 99.", "danger")
                return redirect(url_for("edit_player", player_id=player.id))
            new_attrs[attr] = val

            new_badges = {}
            for badge in badge_list:
                level = request.form.get(badge, "None")
                if level not in BADGE_LEVELS:
                    flash(f"Invalid level for {format_attribute_name(badge)}.", "danger")
                    return redirect(url_for("edit_player", player_id=player.id))
                new_badges[badge] = level

            player.name = name
            for attr, val in new_attrs.items():
                setattr(player, attr, val)
            for badge, level in new_badges.items():
                setattr(player, badge, level)
            db.session.commit()

            flash("Player updated successfully.", "success")
            return redirect(url_for("edit_player", player_id=player.id))

    # GET
    player = None
    if "player_id" in request.args:
        player = Player.query.get_or_404(request.args.get("player_id"))
        if player.user_id != current_user.id:
            flash("You do no have permission to edit this player.", "danger")
            return redirect(url_for("dashboard"))

    return render_template(
        "edit_player.html",
        players=players,
        player=player,
        attribute_list=attribute_list,
        badge_list=badge_list,
        badge_levels=BADGE_LEVELS,
    )
