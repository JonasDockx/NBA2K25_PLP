"""
We define the routes for registration and login.
"""

import random
import json
import string
import requests

from flask import abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import login_user, current_user, logout_user, login_required
from authlib.integrations.flask_client import OAuth
from werkzeug.security import generate_password_hash
from app import app, db, bcrypt
from app.models import (
    User,
    Player,
    UserSettings,
    create_rows_for,
)
from app.game_versions import (
    BADGE_LEVELS,
    DEFAULT_BADGE_LEVEL,
    DEFAULT_GAME_VERSION,
    DEFAULT_TARGET_ATTRIBUTE_VALUE,
    DEFAULT_TARGET_BADGE_LEVEL,
    MAX_ATTRIBUTE_VALUE,
    MIN_ATTRIBUTE_VALUE,
    all_versions,
    attribute_upgrade_cost,
    attributes_for,
    badge_upgrade_cost,
    badges_for,
    display_name,
    is_valid_version,
    next_badge_level,
    version_label,
)
from utils.mailer import send_email
from utils.tokens import generate_confirmation_token, confirm_token
from utils.scrape_2kratings import scrape_player_data

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

def get_owned_player(player_id):
    """
    Fetch a player by id, 404 if missing, 403 if not owned by current_user.
    """
    player = Player.query.get_or_404(player_id)
    if player.user_id != current_user.id:
        abort(403)
    return player

def rows_for(player):
    """
    The player's attribute and badge rows, keyed by attribute_key / badge_key.

    Every row exists from the moment the player is created (see
    models.create_rows_for), and only for the keys the player's own Game
    Version has. So a lookup that misses is not "no row yet" - it means the
    key does not belong to this player at all, which is exactly what the
    routes below reject.
    """
    attributes = {row.attribute_key: row for row in player.attributes}
    badges = {row.badge_key: row for row in player.badges}
    return attributes, badges


def whole_number(raw, default):
    """`raw` as an int, or `default` if it is missing or not a number."""
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def version_choices():
    """(key, label) pairs for the create-player dropdown, oldest first."""
    return [(version, version_label(version)) for version in all_versions()]


def badge_version_map():
    """
    Every badge key that exists in any Game Version, mapped to the versions it
    belongs to.

    The create-player form renders all of them and hides the ones that do not
    apply to the version picked in the dropdown, so it needs to know which is
    which. Only the form uses this - the routes never trust it, they check
    against the player's own rows.
    """
    keys = sorted({key for version in all_versions() for key in badges_for(version)})
    return {
        key: [version for version in all_versions() if key in badges_for(version)]
        for key in keys
    }

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

    The 40 form reads and 40 constructor arguments this route used to carry are
    gone. What exists for a player now comes from its Game Version, so the
    loops below are the same code whether that version has 40 badges or 53.
    """
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Player name cannot be empty.", "danger")
            return redirect(url_for("add_player"))

        # The Game Version decides which keys are legal for every loop below,
        # so it is validated before anything else. It is a form value and
        # therefore hostile: Player.validate_game_version would refuse a bad
        # one too, but as a 500 rather than as something a user can read.
        version = request.form.get("game_version")
        if not is_valid_version(version):
            flash("Please choose a Game Version for this player.", "danger")
            return redirect(url_for("add_player"))

        player = Player(
            name=name,
            user_id=current_user.id,
            game_version=version,
            devpoints=whole_number(request.form.get("devpoints"), 0),
            badgepoints=whole_number(request.form.get("badgepoints"), 0),
        )
        create_rows_for(player)
        db.session.add(player)

        # create_rows_for has already given the player a full set of rows at
        # the defaults, so a field left blank keeps its default rather than
        # needing a fallback spelled out here. Anything the form sends for a
        # key this version does not have is ignored: the loops walk the
        # player's own rows, never the submitted field names.
        attributes, badges = rows_for(player)

        for key, row in attributes.items():
            raw = request.form.get(key)
            if raw is None or raw == "":
                continue
            value = whole_number(raw, None)
            if value is None:
                db.session.rollback()
                flash(f"{display_name(key)} must be a number.", "danger")
                return redirect(url_for("add_player"))
            if value < MIN_ATTRIBUTE_VALUE or value > MAX_ATTRIBUTE_VALUE:
                db.session.rollback()
                flash(
                    f"{display_name(key)} must be between {MIN_ATTRIBUTE_VALUE} "
                    f"and {MAX_ATTRIBUTE_VALUE}.",
                    "danger",
                )
                return redirect(url_for("add_player"))
            row.value = value

        for key, row in badges.items():
            level = request.form.get(key, DEFAULT_BADGE_LEVEL)
            if level not in BADGE_LEVELS:
                db.session.rollback()
                flash(f"Invalid level for {display_name(key)}.", "danger")
                return redirect(url_for("add_player"))
            row.level = level

        db.session.commit()

        flash("Player added successfully!", "success")
        return redirect(url_for("add_player"))

    # Render the form when accessed via GET request. Attributes are the same in
    # every Game Version, so one list serves the whole form; badges are not,
    # so all of them are rendered and the form hides the ones that do not
    # apply to the version picked.
    return render_template(
        "add_player.html",
        versions=version_choices(),
        attribute_list=attributes_for(DEFAULT_GAME_VERSION),
        badge_versions=badge_version_map(),
        badge_levels=BADGE_LEVELS,
        display_name=display_name,
    )

@app.route("/input_stats", methods=["GET", "POST"])
@login_required
def input_stats():
    """
    Inputting the game statistics.
    """
    if request.method == "POST":
        # Fetch the player
        player_id = request.form.get("player_id")
        player = get_owned_player(player_id)

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

    The economy itself is unchanged - costs are identical in every Game
    Version. What changed is where values are read and written: rows looked up
    once into a dict, instead of 76 getattr calls against the player.
    """
    if request.method == "POST":
        player_id = request.form.get("player_id")
        if not player_id:
            return redirect(url_for("upgrade_attribute"))

        player = get_owned_player(player_id)
        attributes, badges = rows_for(player)

        # Upgrade an attribute with devpoints.
        attribute = request.form.get("attribute")
        if attribute:
            row = attributes.get(attribute)
            if row is None:
                flash("That attribute does not exist for this player.", "danger")
                return redirect(url_for("upgrade_attribute", player_id=player.id))

            if row.value >= MAX_ATTRIBUTE_VALUE:
                flash(f"{display_name(attribute)} is already at the maximum value!", "info")
                return redirect(url_for("upgrade_attribute", player_id=player.id))

            cost = attribute_upgrade_cost(row.value)
            if player.devpoints >= cost:
                player.devpoints -= cost
                row.value += 1
                db.session.commit()
                flash(
                    f"Success! {display_name(attribute)} upgraded to {row.value}. "
                    f"{cost} devpoints used.",
                    "success"
                )
            else:
                flash("Not enough development points to upgrade this attribute.", "danger")

        # Upgrade a badge with devpoints. The key is checked against the
        # player's own badge rows, so a hand-crafted POST cannot upgrade a
        # badge that does not exist in this player's Game Version.
        badge_devpoints = request.form.get("badge_devpoints")
        if badge_devpoints:
            row = badges.get(badge_devpoints)
            if row is None:
                flash("That badge does not exist for this player's Game Version.", "danger")
                return redirect(url_for("upgrade_attribute", player_id=player.id))

            next_level = next_badge_level(row.level)
            if next_level is None:
                flash(f"{display_name(badge_devpoints)} is already at the maximum level.", "info")
                return redirect(url_for("upgrade_attribute", player_id=player.id))

            badge_cost = badge_upgrade_cost(row.level)
            if player.devpoints >= badge_cost:
                player.devpoints -= badge_cost
                row.level = next_level
                db.session.commit()
                flash(
                    f"Success! {display_name(badge_devpoints)} upgraded to {next_level}. "
                    f"{badge_cost} devpoints used.",
                    "success"
                )
            else:
                flash("Not enough development points to upgrade this badge.", "danger")

        # Upgrade a badge with a badge point - one point, any level.
        badge_badgepoints = request.form.get("badge_badgepoints")
        if badge_badgepoints:
            row = badges.get(badge_badgepoints)
            if row is None:
                flash("That badge does not exist for this player's Game Version.", "danger")
                return redirect(url_for("upgrade_attribute", player_id=player.id))

            next_level = next_badge_level(row.level)
            if next_level is None:
                flash(f"{display_name(badge_badgepoints)} is already at the maximum level.", "info")
                return redirect(url_for("upgrade_attribute", player_id=player.id))

            if player.badgepoints > 0:
                row.level = next_level
                player.badgepoints -= 1
                db.session.commit()
                flash(
                    f"Success! {display_name(badge_badgepoints)} upgraded to "
                    f"{next_level} with 1 badge point.",
                    "success"
                )
            else:
                flash("Not enough points to upgrade this badge.", "danger")

        return redirect(url_for("upgrade_attribute", player_id=player.id))

    # Handle GET request: display the player and attributes
    player = None
    attribute_list = []
    badge_list = []
    values = {}
    target_values = {}
    levels = {}
    target_badges = {}

    if "player_id" in request.args:
        player = get_owned_player(request.args.get("player_id"))
        attributes, badges = rows_for(player)
        # Driven by the player's own Game Version, so a 2K26 player is never
        # offered a 2K27 badge and vice versa.
        attribute_list = attributes_for(player.game_version)
        badge_list = badges_for(player.game_version)
        values = {key: row.value for key, row in attributes.items()}
        target_values = {key: row.target_value for key, row in attributes.items()}
        levels = {key: row.level for key, row in badges.items()}
        target_badges = {key: row.target_level for key, row in badges.items()}

    # Fetch only the players created by the logged-in user
    players = Player.query.filter_by(user_id=current_user.id).all()

    return render_template(
        "upgrade_attribute.html",
        players=players,
        player=player,
        values=values,
        target_values=target_values,
        levels=levels,
        target_badges=target_badges,
        attribute_list=attribute_list,
        badge_list=badge_list,
        badge_levels=BADGE_LEVELS,
        display_name=display_name,
        version_label=version_label,
    )

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
    # The same message whether or not the address is registered, so that this
    # form cannot be used to discover which e-mail addresses have accounts.
    sent_message = (
        "If an account exists for that e-mail address, we've sent a password "
        "reset link. Please check your inbox and your spam folder."
    )

    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if not user:
            flash(sent_message, "info")
            return render_template("forgot_password.html")

        token = generate_confirmation_token(user.email)
        reset_url = url_for("reset_password", token=token, _external=True)

        was_sent = send_email(
            user.email,
            "Reset Your Password",
            f"Click the link to reset your password: {reset_url}"
        )

        if was_sent:
            flash(sent_message, "info")
        else:
            flash(
                "Something went wrong on our end and we couldn't send the "
                "e-mail. Please try again in a few minutes.",
                "danger"
            )

    return render_template("forgot_password.html")

@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Resetting the user's password."""
    # confirm_token returns False rather than raising, so this must be an
    # explicit check - a try/except here would never fire.
    email = confirm_token(token)
    if not email:
        flash("The password reset link is invalid or has expired.", "danger")
        return redirect(url_for("forgot_password"))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("The password reset link is invalid or has expired.", "danger")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("reset_password", token=token))

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
    player = get_owned_player(player_id)

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

    Targets used to live in PlayerTargets, a second wide table repeating all 76
    columns. They are now target_value / target_level on the same row as the
    value they are aimed at, so this route mostly got shorter.
    """
    players = Player.query.filter_by(user_id=current_user.id).all()
    selected_player = None
    attribute_list = []
    badge_list = []
    target_values = {}
    target_badges = {}

    if request.method == "POST":
        player_id = request.form.get("player_id")
        if player_id:
            selected_player = get_owned_player(player_id)
            attributes, badges = rows_for(selected_player)
            attribute_list = attributes_for(selected_player.game_version)
            badge_list = badges_for(selected_player.game_version)
            target_values = {key: row.target_value for key, row in attributes.items()}
            target_badges = {key: row.target_level for key, row in badges.items()}

            if "scrape_player" in request.form:
                player_url_part = request.form.get("player_url_part")
                if player_url_part:
                    scraped_data = scrape_player_data(player_url_part)
                    if "error" not in scraped_data:
                        # Only keys this player's Game Version has are filled
                        # in. 2Kratings serves one game's ratings and does not
                        # know which version this player is being tracked in.
                        scraped_attributes = scraped_data.get("attributes", {})
                        for key in attribute_list:
                            if key in scraped_attributes:
                                target_values[key] = scraped_attributes[key]

                        scraped_badges = scraped_data.get("badges", {})
                        for key in badge_list:
                            target_badges[key] = scraped_badges.get(key, DEFAULT_BADGE_LEVEL)

                        flash("Player data scraped successfully!", "success")
                    else:
                        flash(scraped_data["error"], "danger")

            elif "save_targets" in request.form:
                # Validate everything before writing anything, so a bad value
                # at the bottom of the form cannot leave the top half saved.
                new_values = {}
                for key in attribute_list:
                    raw = request.form.get(f"target_{key}", DEFAULT_TARGET_ATTRIBUTE_VALUE)
                    value = whole_number(raw, None)
                    if value is None:
                        flash(f"Target for {display_name(key)} must be a number.", "danger")
                        return redirect(url_for("target_settings", player_id=selected_player.id))
                    if value < MIN_ATTRIBUTE_VALUE or value > MAX_ATTRIBUTE_VALUE:
                        flash(
                            f"Target for {display_name(key)} must be between "
                            f"{MIN_ATTRIBUTE_VALUE} and {MAX_ATTRIBUTE_VALUE}.",
                            "danger",
                        )
                        return redirect(url_for("target_settings", player_id=selected_player.id))
                    new_values[key] = value

                new_levels = {}
                for key in badge_list:
                    level = request.form.get(f"target_{key}", DEFAULT_TARGET_BADGE_LEVEL)
                    if level not in BADGE_LEVELS:
                        flash(f"Invalid target level for {display_name(key)}.", "danger")
                        return redirect(url_for("target_settings", player_id=selected_player.id))
                    new_levels[key] = level

                for key, value in new_values.items():
                    attributes[key].target_value = value
                for key, level in new_levels.items():
                    badges[key].target_level = level

                db.session.commit()
                flash("Target values saved successfully!", "success")

                return redirect(url_for("target_settings", player_id=selected_player.id))

    elif "player_id" in request.args:
        # The save above redirects back here with the player in the URL, so the
        # GET has to fill the form in or the user lands on an empty page.
        selected_player = get_owned_player(request.args.get("player_id"))
        attributes, badges = rows_for(selected_player)
        attribute_list = attributes_for(selected_player.game_version)
        badge_list = badges_for(selected_player.game_version)
        target_values = {key: row.target_value for key, row in attributes.items()}
        target_badges = {key: row.target_level for key, row in badges.items()}

    return render_template(
        "target_settings.html",
        players=players,
        selected_player=selected_player,
        target_values=target_values,
        target_badges=target_badges,
        attribute_list=attribute_list,
        badge_list=badge_list,
        badge_levels=BADGE_LEVELS,
        display_name=display_name,
        version_label=version_label,
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

@app.route("/edit_player", methods=["GET", "POST"])
@login_required
def edit_player():
    """
    Allows the user to edit a player's name, attributes and badges in case
    of an error at player creation.

    This is the Correction tool: it writes values straight in, outside the
    points economy, exactly as before. See
    docs/adr/0001-correction-tool-bypasses-points-economy.md.
    """
    players = Player.query.filter_by(user_id=current_user.id).all()

    if request.method == "POST":
        player = get_owned_player(request.form.get("player_id"))
        attributes, badges = rows_for(player)

        # Validate everything before writing anything, so a bad value at the
        # bottom of the form cannot leave the top half saved.
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Player name cannot be empty.", "danger")
            return redirect(url_for("edit_player", player_id=player.id))

        new_values = {}
        for key in attributes:
            value = whole_number(request.form.get(key), None)
            if value is None:
                flash(f"{display_name(key)} must be a number.", "danger")
                return redirect(url_for("edit_player", player_id=player.id))
            if value < MIN_ATTRIBUTE_VALUE or value > MAX_ATTRIBUTE_VALUE:
                flash(
                    f"{display_name(key)} must be between {MIN_ATTRIBUTE_VALUE} "
                    f"and {MAX_ATTRIBUTE_VALUE}.",
                    "danger",
                )
                return redirect(url_for("edit_player", player_id=player.id))
            new_values[key] = value

        new_levels = {}
        for key in badges:
            level = request.form.get(key, DEFAULT_BADGE_LEVEL)
            if level not in BADGE_LEVELS:
                flash(f"Invalid level for {display_name(key)}.", "danger")
                return redirect(url_for("edit_player", player_id=player.id))
            new_levels[key] = level

        player.name = name
        for key, value in new_values.items():
            attributes[key].value = value
        for key, level in new_levels.items():
            badges[key].level = level
        db.session.commit()

        flash("Player updated successfully.", "success")
        return redirect(url_for("edit_player", player_id=player.id))

    # GET
    player = None
    attribute_list = []
    badge_list = []
    values = {}
    levels = {}

    if "player_id" in request.args:
        player = get_owned_player(request.args.get("player_id"))
        attributes, badges = rows_for(player)
        # Only the badges of this player's own Game Version are offered.
        attribute_list = attributes_for(player.game_version)
        badge_list = badges_for(player.game_version)
        values = {key: row.value for key, row in attributes.items()}
        levels = {key: row.level for key, row in badges.items()}

    return render_template(
        "edit_player.html",
        players=players,
        player=player,
        values=values,
        levels=levels,
        attribute_list=attribute_list,
        badge_list=badge_list,
        badge_levels=BADGE_LEVELS,
        display_name=display_name,
        version_label=version_label,
    )
