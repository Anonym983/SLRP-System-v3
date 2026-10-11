import io
import os
import re
import time
import sqlite3
import datetime
import traceback
from typing import Union
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

# =====================================================================================
# 1) DESIGN: Farben, Texte, Bilder und Namen kannst du hier selbst ändern
#    Farben sind Hex-Codes: 0x + 6 Zeichen (z. B. 0xFF0000 = Rot)
# =====================================================================================
DESIGN = {
    "ICON": "🌟",                       # steht vor der Kopfzeile jedes Embeds
    "BRAND": "Made by Timo",          # Kopfzeile, z. B. "🚨 NOTRUF HAMBURG · TEAM"
    "FOOTER": "Powered by SLRP System",
    "FOOTER_TEAM": "Powerded by SLRP System",
    "FOOTER_TICKET": "Powered by SLRP System",
    "PRIMARY": 0xE53935,    # Hauptfarbe: Rot
    "SUCCESS": 0x2ECC71,    # Grün
    "ERROR": 0xB71C1C,      # Dunkelrot
    "WARN": 0xFF9800,       # Orange
    "NEUTRAL": 0x6B7A8F,    # Grau (Logs)
    "ACCENT": 0x9B5DE5,     # Lila (Feedback, Umfragen)
    "INFO": 0x3498DB,       # Blau (Infos)
    "BANNER": "",           # Optional: Link zu einem Bild, das unter Panels erscheint (leer = aus)
    "LOGO": "",             # Optional: Link zu einem kleinen Logo neben der Kopfzeile (leer = aus)
    "STATUS": "Notruf Hamburg RP",
    "WELCOME_TEXT": "Willkommen auf dem Server SLRP, {user} Schau dir kurz das Regelwerk an, damit du vorbeireitet bist. Viel Spaß wünscht dir Streetlife-Rp|VC!⭐️",
    "LEAVE_TEXT": "Tschüss {name} danke das du auf SLRP warst bis bald🌟",
    "VERIFY_TEXT": "Verifiziere dich um den vollständigen Discord Server zu sehen danke!✅",
    "MAX_WARNS": 3,
}

# Ticket-Kategorien: (Schlüssel, Name, Emoji, Beschreibung, Rolle die das Ticket sieht)
TICKET_KATEGORIEN = [
    ("support", "Normaler Support", "🎫", "Allgemeine Fragen und Hilfe", "TEAM_ROLE"),
    ("haeuser", "Häuser & Waffenschein", "🏠", "Hauskauf, Waffenschein usw.", "TEAM_ROLE"),
    ("entbannung", "Entbannung", "🔓", "Antrag auf Entbannung", "TEAM_ROLE"),
    ("beschwerde", "Team-Beschwerde", "📢", "Beschwerden über das Team", "HIGHTEAM_ROLE"),
    ("creator", "Content Creator", "🎨", "Bewerbung als Creator", "TEAM_ROLE"),
    ("highteam", "High Team", "👑", "Nur für das High Team", "HIGHTEAM_ROLE"),
    ("partner", "Partnerschaften", "🤝", "Partneranfragen", "HIGHTEAM_ROLE"),
    ("fraktion", "Fraktion", "🏛️", "Fraktion eintragen", "TEAM_ROLE"),
    ("owner", "Owner", "👔", "Anliegen an die Serverleitung", "OWNER_ROLE"),
]

# Antragssystem (Ausweis, Führerscheine, Waffenscheine): (Schlüssel, Name, Emoji, Beschreibung)
ANTRAEGE = [
    ("ausweis", "Personalausweis beantragen", "🪪", "Beantrage einen Ingame Personalausweis"),
    ("pkw", "Führerschein (PKW)", "🚗", "Führerschein Klasse PKW"),
    ("lkw", "Führerschein (LKW)", "🚚", "Führerschein Klasse LKW"),
    ("moto", "Führerschein (Motorrad)", "🏍️", "Führerschein Klasse Motorrad"),
    ("kws", "Kleiner Waffenschein", "🔫", "Kleiner Waffenschein"),
    ("gws", "Großer Waffenschein", "🎯", "Großer Waffenschein"),
]
SCHEIN_NAMEN = {k: n for k, n, _, _ in ANTRAEGE if k != "ausweis"}

# Zeigt in den Teamlisten Online-Status (🟢🟠🔴⚫). Dafür muss im Developer Portal unter Bot
# zusätzlich der "Presence Intent" eingeschaltet sein. Sonst auf False lassen.
SHOW_STATUS = False

# =====================================================================================
# 2) EINSTELLUNGEN: IDs (0 = nicht eingerichtet)
# =====================================================================================
TOKEN = os.getenv("DISCORD_TOKEN")  # kommt vom Hoster (Variable), nie in den Code schreiben

CFG = {
    "LOG_CHANNEL": 1558571057999511643,
    "WELCOME_CHANNEL": 1557814941527056396,
    "LEAVE_CHANNEL": 1557814950137692277,
    "ALERT_CHANNEL": 1558572041550958683,
    "RP_CHANNEL": 1557814995683909662,
    "TICKET_CATEGORY": 1557814916101050469,
    "VERIFY_ROLE": 1557814738988310678,
    "TEAM_ROLE": 1557814706457018438,
    "SUPPORT_ROLE": 1557814706457018438,
    "SUPPORT_VC": 1557814994614227134, "SUPPORT_PING": 1557815189456556082,
    "HIGHTEAM_VC": 1557815075492864032, "HIGHTEAM_PING": 1557815191901569078,
    "BUERO_VC": 1557815118899716226, "BUERO_PING": 1558570781892550779,
    "TEAMLOG_CHANNEL": 1557815289033531523,
    "FEEDBACK_CHANNEL": 1557815164940845106,
    "RP_PING_ROLE": 1557814802670297240,
    "HIGHTEAM_ROLE": 1557814659778879587,
    "OWNER_ROLE": 1557814639113281607,
    "NEWS_PING_ROLE": 1557814816704565279,
    "EVENT_PING_ROLE": 1557814799637680223,
    "GIVEAWAY_PING_ROLE": 1557814818726084689,
    "PARTNER_PING_ROLE": 1557814801168601172,
    "FRAKTION_PING_ROLE": 1558577674534920192,
    "TEAM_UPDATES_ROLE": 1557814798400356453,
    "BAU_PING": 1557814796793942108,
    # Neu: bitte eintragen (0 = noch nicht eingerichtet)
    "KONTROLL_CHANNEL": 1557815068756943000,   # Channel "Discord-Kontrolle": nur dort funktioniert "." und Annehmen (0 = überall)
    "FRAKTION_CHANNEL": 1557815085680824380,   # Channel für Fraktions-Updates (0 = Team-Log-Channel)
    "ANTRAG_CHANNEL": 1558823634842165358,     # Channel, in dem Anträge (Ausweis, Führerschein) landen (0 = Team-Log-Channel)
    "RECHTE_CHANNEL": 1557815260235436232,     # Channel für Rechte-Anfragen (0 = Team-Log-Channel)
}

# Self-Roles-Buttons: (Name, Emoji, Rollen-Schlüssel aus CFG)
PING_ROLLEN = [
    ("News", "📣", "NEWS_PING_ROLE"),
    ("RP", "🟩", "RP_PING_ROLE"),
    ("Fraktion", "🏛️", "FRAKTION_PING_ROLE"),
    ("Partner", "🤝", "PARTNER_PING_ROLE"),
    ("Giveaway", "🎀", "GIVEAWAY_PING_ROLE"),
    ("Event", "🪩", "EVENT_PING_ROLE"),
    ("Team Update", "🛡️", "TEAM_UPDATES_ROLE"),
    ("Bau Updates", "🔨", "BAU_PING"),
]
# =====================================================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True
intents.presences = SHOW_STATUS
bot = commands.Bot(command_prefix="!", intents=intents)
START_TIME = time.time()
DEFAULT_DESIGN = dict(DESIGN)
DEFAULT_CFG = dict(CFG)


# ------------------------------ Datenbank ------------------------------
def db(q, args=(), fetch=False):
    with sqlite3.connect(os.getenv("DB_PATH", "bot.db")) as c:
        cur = c.execute(q, args)
        return cur.fetchall() if fetch else None


for t in [
    "CREATE TABLE IF NOT EXISTS roblox(uid INTEGER PRIMARY KEY, name TEXT)",
    "CREATE TABLE IF NOT EXISTS teamrang(uid INTEGER PRIMARY KEY, rolle INTEGER)",
    "CREATE TABLE IF NOT EXISTS warns(uid INTEGER, grund TEXT, von INTEGER)",
    "CREATE TABLE IF NOT EXISTS mwarns(uid INTEGER, grund TEXT, von INTEGER, zeit TEXT)",
    "CREATE TABLE IF NOT EXISTS icsperre(uid INTEGER PRIMARY KEY, grund TEXT)",
    "CREATE TABLE IF NOT EXISTS houses(name TEXT PRIMARY KEY, besitzer INTEGER)",
    "CREATE TABLE IF NOT EXISTS abmeldungen(uid INTEGER PRIMARY KEY, bis TEXT, grund TEXT)",
    "CREATE TABLE IF NOT EXISTS dienst(uid INTEGER PRIMARY KEY, start REAL)",
    "CREATE TABLE IF NOT EXISTS dienstzeit(uid INTEGER PRIMARY KEY, sek INTEGER)",
    "CREATE TABLE IF NOT EXISTS notizen(uid INTEGER, text TEXT, von INTEGER, zeit TEXT)",
    "CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)",
    "CREATE TABLE IF NOT EXISTS fraktionen(name TEXT PRIMARY KEY, owner INTEGER, anwesen INTEGER)",
    "CREATE TABLE IF NOT EXISTS ausweis(uid INTEGER PRIMARY KEY, name TEXT, geburt TEXT, roblox TEXT, "
    "pkw INTEGER DEFAULT 0, lkw INTEGER DEFAULT 0, moto INTEGER DEFAULT 0, kws INTEGER DEFAULT 0, gws INTEGER DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS acheck(id INTEGER PRIMARY KEY AUTOINCREMENT, msg_id INTEGER, channel_id INTEGER, "
    "role_id INTEGER, title TEXT, beschr TEXT, ende REAL, status TEXT, von INTEGER)",
    "CREATE TABLE IF NOT EXISTS acheck_resp(check_id INTEGER, uid INTEGER, PRIMARY KEY(check_id, uid))",
]:
    db(t)


def get_setting(key, default=None):
    r = db("SELECT value FROM settings WHERE key=?", (key,), fetch=True)
    return r[0][0] if r else default


def set_setting(key, value):
    db("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, str(value)))


COLOR_KEYS = {"PRIMARY", "SUCCESS", "ERROR", "WARN", "NEUTRAL", "ACCENT", "INFO"}


def load_overrides():
    """Werte, die du in Discord mit /design_setzen und /config_setzen geändert hast, überschreiben den Code."""
    for k in DESIGN:
        v = get_setting("design:" + k)
        if v is None:
            continue
        try:
            if k in COLOR_KEYS:
                DESIGN[k] = int(v, 16)
            elif k == "MAX_WARNS":
                DESIGN[k] = int(v)
            else:
                DESIGN[k] = v
        except ValueError:
            pass
    for k in CFG:
        v = get_setting("cfg:" + k)
        if v is not None and v.isdigit():
            CFG[k] = int(v)


load_overrides()


# ------------------------------ Design-Bausteine ------------------------------
def card(kind, title, desc="", color=None, fields=None, thumb=None, image=None, footer=None, banner=False):
    """Das Standard-Embed: Kopfzeile, Titel, Text, Kacheln (Felder), Footer + Zeit."""
    e = discord.Embed(
        title=title[:256] if title else None,
        description=desc[:4096] if desc else None,
        color=color if color is not None else DESIGN["PRIMARY"],
        timestamp=discord.utils.utcnow(),
    )
    e.set_author(name=f"{DESIGN['ICON']} {DESIGN['BRAND']} · {kind}".upper(), icon_url=DESIGN["LOGO"] or None)
    for name, value, inline in fields or []:
        e.add_field(name=str(name)[:256], value=str(value)[:1024] or "—", inline=inline)
    e.set_footer(text=(footer or DESIGN["FOOTER"])[:2048])
    if thumb:
        e.set_thumbnail(url=thumb)
    if image:
        e.set_image(url=image)
    elif banner and DESIGN["BANNER"]:
        e.set_image(url=DESIGN["BANNER"])
    return e


def team_card(title, color, fields, thumb=None):
    return card("TEAM", title, color=color, fields=fields, thumb=thumb, footer=DESIGN["FOOTER_TEAM"])


def list_card(kind, title, lines, empty, color=None):
    text = ""
    for n, line in enumerate(lines):
        if len(text) + len(line) + 1 > 3900:
            text += f"\n… und {len(lines) - n} weitere"
            break
        text += line + "\n"
    return card(kind, title, text or empty, color)


def chunk_blocks(blocks, limit=3800):
    texts, cur = [], ""
    for b in blocks:
        if len(cur) + len(b) > limit:
            texts.append(cur)
            cur = ""
        cur += b + "\n"
    texts.append(cur)
    return texts


def warn_bar(n):
    m = DESIGN["MAX_WARNS"]
    return f"{'🟥' * min(n, m)}{'⬜' * max(m - n, 0)}  {n}/{m}"


def fmt_dur(sec):
    sec = int(sec)
    h, r = divmod(sec, 3600)
    m = r // 60
    return f"{h} Std. {m} Min." if h else f"{m} Min."


def is_team(member: discord.Member):
    return member.guild_permissions.administrator or any(
        r.id == CFG["TEAM_ROLE"] for r in member.roles
    )


def pick_channel(guild, *keys):
    """Gibt den ersten gesetzten Channel aus CFG zurück."""
    for k in keys:
        ch = guild.get_channel(CFG.get(k, 0))
        if ch:
            return ch
    return None


async def log(guild, text, file=None):
    ch = guild.get_channel(CFG["LOG_CHANNEL"])
    if ch:
        await ch.send(embed=card("LOG", "📋 Bot-Log", text, DESIGN["NEUTRAL"]), file=file)


def team_only():
    return app_commands.check(lambda i: is_team(i.user))


async def post_team(i: discord.Interaction, embed: discord.Embed, logtext: str):
    ch = i.guild.get_channel(CFG["TEAMLOG_CHANNEL"])
    if ch and ch.id != i.channel.id:
        await ch.send(embed=embed)
        await i.response.send_message(f"Eingetragen in {ch.mention}.", ephemeral=True)
    else:
        await i.response.send_message(embed=embed)
    await log(i.guild, logtext)


async def edit_panel(guild, key, **kwargs):
    """Aktualisiert ein automatisch gepflegtes Panel (Teamliste, Fraktionsliste, Serverstatus)."""
    ref = get_setting(key)
    if not ref:
        return
    try:
        cid, mid = ref.split(":")
        ch = guild.get_channel(int(cid))
        msg = await ch.fetch_message(int(mid))
        await msg.edit(**kwargs)
    except Exception:
        pass


async def dm_user(guild, uid, text):
    m = guild.get_member(uid)
    if m:
        try:
            await m.send(text)
        except discord.HTTPException:
            pass


def get_rank(uid):
    r = db("SELECT rolle FROM teamrang WHERE uid=?", (uid,), fetch=True)
    return r[0][0] if r else None


async def apply_rank(guild, member, old_id, new_role):
    try:
        old = guild.get_role(old_id) if old_id else None
        if old and old != new_role:
            await member.remove_roles(old)
        if new_role:
            await member.add_roles(new_role)
        team = guild.get_role(CFG["TEAM_ROLE"])
        if team:
            await member.add_roles(team)
        return True
    except discord.Forbidden:
        return False


@bot.tree.error
async def on_tree_error(i: discord.Interaction, err):
    if isinstance(err, app_commands.CheckFailure):
        msg = "Dafür hast du keine Berechtigung."
    else:
        traceback.print_exception(type(err), err, err.__traceback__)
        msg = "Da ist ein Fehler passiert. Bitte versuche es nochmal."
    if i.response.is_done():
        await i.followup.send(msg, ephemeral=True)
    else:
        await i.response.send_message(msg, ephemeral=True)


# ------------------------------ Teamliste / Fraktionsliste (Panels) ------------------------------
def status_dot(m):
    if not SHOW_STATUS or m is None:
        return "▫️"
    return {"online": "🟢", "idle": "🟠", "dnd": "🔴"}.get(str(m.status), "⚫")


def team_embeds(guild):
    rows = db("SELECT uid, rolle FROM teamrang", fetch=True)
    if not rows:
        return [card("TEAM", "👥 Teamliste", "Keine Teammitglieder eingetragen.", banner=True)]
    groups = {}
    for uid, rid in rows:
        groups.setdefault(rid, []).append(uid)

    def pos(kv):
        r = guild.get_role(kv[0])
        return r.position if r else -1

    blocks = []
    for rid, uids in sorted(groups.items(), key=pos, reverse=True):
        role = guild.get_role(rid)
        head = f"🔻 **{role.mention if role else 'Unbekannter Rang'}** · `{len(uids)}`"
        lines = "\n".join(f"┃ {status_dot(guild.get_member(u))} <@{u}>" for u in uids)
        blocks.append(f"{head}\n{lines}\n")
    texts = chunk_blocks(blocks)
    return [card("TEAM", f"👥 Teamliste · {len(rows)} Mitglieder" if n == 0 else None, text, banner=(n == 0))
            for n, text in enumerate(texts[:10])]


def fraktion_embeds(guild):
    rows = db("SELECT name,owner,anwesen FROM fraktionen ORDER BY name COLLATE NOCASE", fetch=True)
    if not rows:
        return [card("FRAKTIONEN", "🏴 Fraktionsliste", "Noch keine Fraktionen eingetragen.", banner=True)]
    total = sum(a for _, _, a in rows)
    blocks = [f"🏴 **{n}**\n┃ 👑 Owner: <@{o}>\n┃ 🏠 Anwesen: **{a}**\n" for n, o, a in rows]
    texts = chunk_blocks(blocks)
    texts[0] = f"📊 **{len(rows)}** Fraktionen · **{total}** Anwesen insgesamt\n\n" + texts[0]
    return [card("FRAKTIONEN", "🏴 Fraktionsliste" if n == 0 else None, text, banner=(n == 0))
            for n, text in enumerate(texts[:10])]


async def refresh_team_panel(guild):
    await edit_panel(guild, "panel_team", embeds=team_embeds(guild))


async def refresh_fraktion_panel(guild):
    await edit_panel(guild, "panel_fraktion", embeds=fraktion_embeds(guild))


# ------------------------------ Serverstatus / RP ------------------------------
def flag(key, default="0"):
    return get_setting(key, default) == "1"


def onoff(v):
    return "🟢 Aktiviert" if v else "🔴 Deaktiviert"


def server_embed():
    on = flag("srv_on")
    code = get_setting("srv_code", "")
    by = get_setting("srv_by")
    ts = get_setting("srv_ts")
    fields = [
        ("📡 Status", "🟢 Geöffnet" if on else "🔴 Geschlossen", True),
        ("🔑 Servercode", f"`{code}`" if (on and code) else "—", True),
        ("🎭 Roleplay-Modus", onoff(flag("srv_rp", "1")), True),
        ("🏗️ Baumodus", onoff(flag("srv_bau")), True),
        ("🎙️ Voice-Chat-Pflicht", onoff(flag("srv_vc")), True),
    ]
    if by and ts:
        fields.append(("🕐 Zuletzt aktualisiert", f"<t:{int(float(ts))}:R> von {by}", False))
    return card("SERVERSTATUS", "🛰️ Serverstatus-Verwaltung", "Mit den Schaltflächen steuert das Team den Serverstatus.",
                DESIGN["SUCCESS"] if on else DESIGN["ERROR"], fields, banner=True)


async def touch_server(guild, user):
    set_setting("srv_by", user.mention)
    set_setting("srv_ts", time.time())
    await edit_panel(guild, "panel_server", embed=server_embed())


async def do_rp_start(guild, user, code, ping=True):
    ch = guild.get_channel(CFG["RP_CHANNEL"])
    role = guild.get_role(CFG["RP_PING_ROLE"])
    set_setting("rp_start", time.time())
    set_setting("rp_code", code)
    set_setting("srv_on", "1")
    set_setting("srv_code", code)
    e = card("ROLEPLAY", "📡 Das RP hat begonnen!", "Es findet eine **öffentliche** Roleplay-Sitzung statt.\nWir freuen uns, dich begrüßen zu dürfen! 👋",
             DESIGN["SUCCESS"],
             [("📡 Status", "🟢 LIVE", True), ("🔑 Servercode", f"`{code}`", True), ("👤 Gestartet von", user.mention, True)],
             banner=True)
    if ch:
        await ch.send(content=role.mention if (role and ping) else None, embed=e)
    await touch_server(guild, user)
    await log(guild, f"{user.mention} hat das RP gestartet (Code {code}).")


async def do_rp_stop(guild, user):
    ch = guild.get_channel(CFG["RP_CHANNEL"])
    start = get_setting("rp_start")
    dauer = fmt_dur(time.time() - float(start)) if start else "unbekannt"
    set_setting("rp_start", "")
    set_setting("srv_on", "0")
    e = card("ROLEPLAY", "🔴 Das RP ist beendet!", "Aktuell findet keine Roleplay-Sitzung statt.\nKomm gerne bei der nächsten Sitzung vorbei! 🎉",
             DESIGN["ERROR"],
             [("📡 Status", "⚫ OFFLINE", True), ("⏱️ Dauer", dauer, True), ("👤 Beendet von", user.mention, True)],
             banner=True)
    if ch:
        await ch.send(embed=e)
    await touch_server(guild, user)
    await log(guild, f"{user.mention} hat das RP beendet (Dauer {dauer}).")


class ServerAnModal(discord.ui.Modal, title="Server öffnen"):
    code = discord.ui.TextInput(label="Servercode", placeholder="z. B. abc123", max_length=40)

    async def on_submit(self, i: discord.Interaction):
        await do_rp_start(i.guild, i.user, self.code.value, True)
        await i.response.send_message("Server geöffnet, RP gestartet.", ephemeral=True)


class ServerPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _guard(self, i):
        if not is_team(i.user):
            await i.response.send_message("Nur das Team kann den Serverstatus ändern.", ephemeral=True)
            return False
        return True

    async def _toggle(self, i, key, default="0"):
        if not await self._guard(i):
            return
        set_setting(key, "0" if flag(key, default) else "1")
        await touch_server(i.guild, i.user)
        await i.response.send_message("Aktualisiert.", ephemeral=True)

    @discord.ui.button(label="Server an", emoji="▶️", style=discord.ButtonStyle.success, custom_id="srv_on")
    async def srv_on(self, i: discord.Interaction, b: discord.ui.Button):
        if await self._guard(i):
            await i.response.send_modal(ServerAnModal())

    @discord.ui.button(label="Server aus", emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="srv_off")
    async def srv_off(self, i: discord.Interaction, b: discord.ui.Button):
        if await self._guard(i):
            await do_rp_stop(i.guild, i.user)
            await i.response.send_message("Server geschlossen, RP beendet.", ephemeral=True)

    @discord.ui.button(label="RP-Modus", emoji="🎭", style=discord.ButtonStyle.secondary, custom_id="srv_rp")
    async def srv_rp(self, i: discord.Interaction, b: discord.ui.Button):
        await self._toggle(i, "srv_rp", "1")

    @discord.ui.button(label="Baumodus", emoji="🏗️", style=discord.ButtonStyle.secondary, custom_id="srv_bau")
    async def srv_bau(self, i: discord.Interaction, b: discord.ui.Button):
        await self._toggle(i, "srv_bau")

    @discord.ui.button(label="Voice-Pflicht", emoji="🎙️", style=discord.ButtonStyle.secondary, custom_id="srv_vc")
    async def srv_vc(self, i: discord.Interaction, b: discord.ui.Button):
        await self._toggle(i, "srv_vc")


# ------------------------------ Verify ------------------------------
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verifizieren", emoji="✅", style=discord.ButtonStyle.success, custom_id="verify_btn")
    async def verify(self, i: discord.Interaction, b: discord.ui.Button):
        role = i.guild.get_role(CFG["VERIFY_ROLE"])
        if role in i.user.roles:
            return await i.response.send_message("Du bist schon verifiziert.", ephemeral=True)
        if role:
            await i.user.add_roles(role)
        await i.response.send_message("Du bist verifiziert!", ephemeral=True)
        await log(i.guild, f"{i.user.mention} hat sich verifiziert.")


# ------------------------------ Tickets ------------------------------
def ticket_role(guild, cfg_key):
    return guild.get_role(CFG.get(cfg_key, 0)) or guild.get_role(CFG["TEAM_ROLE"])


async def create_ticket(i: discord.Interaction, key: str):
    g = i.guild
    _, label, emoji, desc, rolle_key = next(k for k in TICKET_KATEGORIEN if k[0] == key)
    for ch in g.text_channels:
        if ch.topic == f"ticket:{i.user.id}":
            return await i.response.edit_message(content=f"Du hast schon ein Ticket: {ch.mention}", embed=None, view=None)
    role = ticket_role(g, rolle_key)
    ow = {
        g.default_role: discord.PermissionOverwrite(view_channel=False),
        i.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
    }
    if role:
        ow[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
    ch = await g.create_text_channel(
        f"{key}-{i.user.name}",
        category=g.get_channel(CFG["TICKET_CATEGORY"]),
        overwrites=ow,
        topic=f"ticket:{i.user.id}",
    )
    e = card("TICKET", f"{emoji} {label}",
             "Beschreibe dein Anliegen bitte so genau wie möglich. Das Team meldet sich bei dir.",
             DESIGN["PRIMARY"],
             [("👤 Ersteller", i.user.mention, True), ("📂 Kategorie", label, True), ("📌 Status", "🟡 Offen", True)],
             footer=DESIGN["FOOTER_TICKET"])
    await ch.send(f"{i.user.mention} {role.mention if role else ''}", embed=e, view=TicketControls())
    await i.response.edit_message(content=f"Ticket erstellt: {ch.mention}", embed=None, view=None)
    await log(g, f"Ticket ({label}) von {i.user.mention} erstellt: {ch.mention}")


class CategorySelect(discord.ui.Select):
    def __init__(self):
        opts = [discord.SelectOption(label=l, value=k, emoji=e, description=d) for k, l, e, d, _ in TICKET_KATEGORIEN]
        super().__init__(placeholder="Wähle eine Kategorie aus...", options=opts)

    async def callback(self, i: discord.Interaction):
        await create_ticket(i, self.values[0])


class CategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(CategorySelect())

    @discord.ui.button(label="Abbrechen", emoji="✖️", style=discord.ButtonStyle.secondary)
    async def cancel(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.edit_message(content="Abgebrochen.", embed=None, view=None)


class TicketOpen(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket öffnen", emoji="🎫", style=discord.ButtonStyle.danger, custom_id="ticket_open")
    async def open(self, i: discord.Interaction, b: discord.ui.Button):
        e = card("SUPPORT", "📂 Kategorie wählen", "Wähle unten die passende Kategorie für dein Ticket.", footer=DESIGN["FOOTER_TICKET"])
        await i.response.send_message(embed=e, view=CategoryView(), ephemeral=True)


class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Übernehmen", emoji="🙋", style=discord.ButtonStyle.success, custom_id="ticket_claim")
    async def claim(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_team(i.user):
            return await i.response.send_message("Nur das Team kann Tickets übernehmen.", ephemeral=True)
        await i.response.send_message(embed=card("TICKET", "🙋 Ticket übernommen", f"{i.user.mention} kümmert sich um dieses Ticket.", DESIGN["SUCCESS"], footer=DESIGN["FOOTER_TICKET"]))
        await log(i.guild, f"{i.user.mention} hat {i.channel.mention} übernommen.")

    @discord.ui.button(label="Schließen", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close(self, i: discord.Interaction, b: discord.ui.Button):
        try:
            owner_id = int((i.channel.topic or "").split(":")[1])
        except Exception:
            owner_id = 0
        if not (is_team(i.user) or i.user.id == owner_id):
            return await i.response.send_message("Das darf nur das Team oder der Ersteller.", ephemeral=True)
        await i.response.send_message("Ticket wird geschlossen und gespeichert …")
        lines = []
        async for m in i.channel.history(limit=None, oldest_first=True):
            if m.content:
                lines.append(f"[{m.created_at:%d.%m.%Y %H:%M}] {m.author}: {m.content}")
        data = io.BytesIO("\n".join(lines).encode("utf-8"))
        name = i.channel.name
        await log(i.guild, f"{name} wurde von {i.user.mention} geschlossen. Verlauf siehe Datei.",
                  file=discord.File(data, filename=f"{name}.txt"))
        await i.channel.delete()


def ticket_panel_card():
    fields = [(f"{e} {l}", d, True) for _, l, e, d, _ in TICKET_KATEGORIEN]
    return card(
        "SUPPORT", "🎫 Support-Center",
        "Du brauchst Hilfe? Öffne ein Ticket, wähle die passende Kategorie und beschreibe dein Anliegen so genau wie möglich.\n"
        "Pro Person ist ein offenes Ticket möglich.",
        DESIGN["PRIMARY"], fields, footer=DESIGN["FOOTER_TICKET"], banner=True,
    )


# ------------------------------ "." Discord-Kontrolle ------------------------------
KONTROLLE_RE = re.compile(r"KONTROLLE:(\d+)")


def in_kontroll(channel_id):
    k = CFG["KONTROLL_CHANNEL"]
    return k == 0 or channel_id == k


class DotRequest(discord.ui.View):
    """Persistent: Die Mitglieds-ID steht im Footer der Nachricht."""
    def __init__(self):
        super().__init__(timeout=None)

    async def _check(self, i):
        ok = i.user.guild_permissions.administrator or any(r.id == CFG["SUPPORT_ROLE"] for r in i.user.roles)
        if not ok:
            await i.response.send_message("Nur Supporter.", ephemeral=True)
            return None
        if not in_kontroll(i.channel.id):
            await i.response.send_message(f"Das geht nur im Channel <#{CFG['KONTROLL_CHANNEL']}>.", ephemeral=True)
            return None
        m = KONTROLLE_RE.search(i.message.embeds[0].footer.text or "") if i.message.embeds else None
        if not m:
            await i.response.send_message("Diese Anfrage ist nicht mehr gültig.", ephemeral=True)
            return None
        return int(m.group(1))

    @discord.ui.button(label="Annehmen", emoji="✅", style=discord.ButtonStyle.success, custom_id="kontrolle_ok")
    async def accept(self, i: discord.Interaction, b: discord.ui.Button):
        uid = await self._check(i)
        if uid is None:
            return
        member = i.guild.get_member(uid)
        if member is None:
            return await i.response.send_message("Das Mitglied ist nicht mehr auf dem Server.", ephemeral=True)
        role = i.guild.get_role(CFG["VERIFY_ROLE"])
        if role:
            await member.add_roles(role)
        e = card("KONTROLLE", "✅ Kontrolle bestanden", color=DESIGN["SUCCESS"],
                 fields=[("👤 Mitglied", member.mention, True), ("🛡️ Supporter", i.user.mention, True), ("📌 Ergebnis", "Angenommen", True)])
        await i.response.edit_message(embed=e, view=None)
        await log(i.guild, f"{i.user.mention} hat {member.mention} angenommen.")

    @discord.ui.button(label="Ablehnen", emoji="⛔", style=discord.ButtonStyle.danger, custom_id="kontrolle_no")
    async def deny(self, i: discord.Interaction, b: discord.ui.Button):
        uid = await self._check(i)
        if uid is None:
            return
        e = card("KONTROLLE", "⛔ Kontrolle abgelehnt", color=DESIGN["ERROR"],
                 fields=[("👤 Mitglied", f"<@{uid}>", True), ("🛡️ Supporter", i.user.mention, True), ("📌 Ergebnis", "Abgelehnt", True)])
        await i.response.edit_message(embed=e, view=None)
        await log(i.guild, f"{i.user.mention} hat <@{uid}> abgelehnt.")


# ------------------------------ Ping-Rollen (Self-Roles) ------------------------------
class PingRoles(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for n, (label, emoji, key) in enumerate(PING_ROLLEN):
            b = discord.ui.Button(label=label, emoji=emoji, style=discord.ButtonStyle.secondary, custom_id=f"pingrole_{n}")
            b.callback = self._make(key)
            self.add_item(b)

    def _make(self, key):
        async def cb(i: discord.Interaction):
            role = i.guild.get_role(CFG.get(key, 0))
            if not role:
                return await i.response.send_message("Diese Rolle ist noch nicht eingerichtet.", ephemeral=True)
            if role in i.user.roles:
                await i.user.remove_roles(role)
                msg = f"Rolle {role.mention} entfernt."
            else:
                await i.user.add_roles(role)
                msg = f"Rolle {role.mention} erhalten."
            await i.response.send_message(msg, ephemeral=True)
        return cb


# ------------------------------ Feedback ------------------------------
class FeedbackModal(discord.ui.Modal, title="Teammitglied bewerten"):
    sterne = discord.ui.TextInput(label="Sterne (1-5)", placeholder="1-5", max_length=1)
    grund = discord.ui.TextInput(label="Warum?", placeholder="Deine Begründung...", style=discord.TextStyle.paragraph, max_length=800)

    def __init__(self, member):
        super().__init__()
        self.member = member

    async def on_submit(self, i: discord.Interaction):
        if not self.sterne.value.isdigit() or not 1 <= int(self.sterne.value) <= 5:
            return await i.response.send_message("Bitte gib bei den Sternen eine Zahl von 1 bis 5 ein.", ephemeral=True)
        n = int(self.sterne.value)
        e = card("FEEDBACK", "💜 Neues Feedback", f"> {self.grund.value}", DESIGN["ACCENT"], [
            ("👤 Teammitglied", self.member.mention, True),
            ("⭐ Bewertung", f"{'⭐' * n}{'▫️' * (5 - n)}  {n}/5", True),
            ("✍️ Von", i.user.mention, True),
        ], thumb=self.member.display_avatar.url)
        ch = i.guild.get_channel(CFG["FEEDBACK_CHANNEL"]) or i.guild.get_channel(CFG["LOG_CHANNEL"])
        if ch:
            await ch.send(embed=e)
        await i.response.send_message("Danke für dein Feedback!", ephemeral=True)
        await log(i.guild, f"{i.user.mention} hat Feedback für {self.member.mention} abgegeben ({n}/5).")


class FeedbackPick(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Wähle ein Teammitglied aus...", min_values=1, max_values=1)
    async def pick(self, i: discord.Interaction, select: discord.ui.UserSelect):
        member = i.guild.get_member(select.values[0].id)
        if member is None or not is_team(member):
            return await i.response.send_message("Das ist kein Teammitglied.", ephemeral=True)
        if member.id == i.user.id:
            return await i.response.send_message("Du kannst dich nicht selbst bewerten.", ephemeral=True)
        await i.response.send_modal(FeedbackModal(member))


class FeedbackOpen(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Feedback geben", emoji="💜", style=discord.ButtonStyle.secondary, custom_id="feedback_open")
    async def open(self, i: discord.Interaction, b: discord.ui.Button):
        e = card("FEEDBACK", "💜 Wen möchtest du bewerten?", "Wähle das Teammitglied aus der Liste.", DESIGN["ACCENT"])
        await i.response.send_message(embed=e, view=FeedbackPick(), ephemeral=True)


# ------------------------------ Einsatz-Meldung ------------------------------
PRIO = {"niedrig": ("🟢 Niedrig", 0x2ECC71), "mittel": ("🟡 Mittel", 0xFF9800), "hoch": ("🔴 Hoch", 0xE53935)}


class EinsatzView(discord.ui.View):
    """Der Zustand (wer übernommen hat) steht im Embed selbst, daher überlebt das einen Neustart."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Übernehmen / Verlassen", emoji="🚨", style=discord.ButtonStyle.danger, custom_id="einsatz_take")
    async def take(self, i: discord.Interaction, b: discord.ui.Button):
        e = i.message.embeds[0]
        idx = next((n for n, f in enumerate(e.fields) if "Einsatzkräfte" in f.name), None)
        if idx is None:
            return await i.response.send_message("Dieser Einsatz ist nicht mehr bearbeitbar.", ephemeral=True)
        ids = re.findall(r"<@(\d+)>", e.fields[idx].value)
        if str(i.user.id) in ids:
            ids.remove(str(i.user.id))
        else:
            ids.append(str(i.user.id))
        e.set_field_at(idx, name="🚑 Einsatzkräfte", value=" ".join(f"<@{x}>" for x in ids) or "—", inline=False)
        await i.response.edit_message(embed=e)

    @discord.ui.button(label="Abschließen", emoji="✅", style=discord.ButtonStyle.success, custom_id="einsatz_close")
    async def close(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_team(i.user):
            return await i.response.send_message("Nur das Team kann Einsätze abschließen.", ephemeral=True)
        e = i.message.embeds[0]
        e.title = "✅ " + (e.title or "Einsatz").replace("🚨 ", "") + " · abgeschlossen"
        e.color = discord.Color(DESIGN["SUCCESS"])
        e.add_field(name="🏁 Abgeschlossen von", value=i.user.mention, inline=True)
        await i.response.edit_message(embed=e, view=None)
        await log(i.guild, f"{i.user.mention} hat einen Einsatz abgeschlossen.")


# ------------------------------ Anträge (Ausweis, Führerschein, Waffenschein, Rechte) ------------------------------
ANTRAG_RE = re.compile(r"ANTRAG:(\w+):(\d+)")
GEBURT_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")


def field_val(embed, name):
    return next((f.value for f in embed.fields if f.name.endswith(name)), None)


def review_result(e, ok, reviewer, reason=None):
    val = "✅ ANGENOMMEN" if ok else "❌ ABGELEHNT"
    idx = next((n for n, f in enumerate(e.fields) if f.name.endswith("Status")), None)
    if idx is None:
        e.add_field(name="📌 Status", value=val, inline=False)
    else:
        e.set_field_at(idx, name="📌 Status", value=val, inline=False)
    if reason:
        e.add_field(name="📝 Grund der Ablehnung", value=reason[:1000], inline=False)
    e.add_field(name="🛡️ Angenommen von" if ok else "🛡️ Abgelehnt von", value=reviewer.mention, inline=True)
    e.color = discord.Color(DESIGN["SUCCESS"] if ok else DESIGN["ERROR"])
    return e


async def send_request(i: discord.Interaction, kind, title, fields, channel_keys, note):
    ch = pick_channel(i.guild, *channel_keys, "TEAMLOG_CHANNEL", "LOG_CHANNEL")
    if not ch:
        return await i.response.send_message("Es ist kein Channel für Anträge eingerichtet.", ephemeral=True)
    e = card("ANTRAG", title, color=DESIGN["WARN"],
             fields=[("👤 Antragsteller", i.user.mention, True)] + fields + [("📌 Status", "🟡 In Prüfung", False)],
             thumb=i.user.display_avatar.url, footer=f"{DESIGN['FOOTER_TEAM']} · ANTRAG:{kind}:{i.user.id}")
    await ch.send(embed=e, view=ReviewView())
    await i.response.send_message(note, ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat einen Antrag gestellt: {title}")


class DenyModal(discord.ui.Modal, title="Antrag ablehnen"):
    grund = discord.ui.TextInput(label="Grund der Ablehnung", style=discord.TextStyle.paragraph, max_length=500)

    def __init__(self, uid, titel):
        super().__init__()
        self.uid = uid
        self.titel = titel

    async def on_submit(self, i: discord.Interaction):
        e = review_result(i.message.embeds[0], False, i.user, self.grund.value)
        await i.response.edit_message(embed=e, view=None)
        await dm_user(i.guild, self.uid, f"❌ Dein Antrag ({self.titel}) wurde abgelehnt.\nGrund: {self.grund.value}")
        await log(i.guild, f"{i.user.mention} hat den Antrag von <@{self.uid}> abgelehnt ({self.titel}).")


class ReviewView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Annehmen", emoji="✅", style=discord.ButtonStyle.success, custom_id="antrag_ok")
    async def ok(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_team(i.user):
            return await i.response.send_message("Nur das Team kann Anträge bearbeiten.", ephemeral=True)
        e = i.message.embeds[0]
        m = ANTRAG_RE.search(e.footer.text or "")
        if not m:
            return await i.response.send_message("Dieser Antrag ist nicht mehr gültig.", ephemeral=True)
        kind, uid = m.group(1), int(m.group(2))
        if kind == "ausweis":
            db("INSERT INTO ausweis(uid,name,geburt,roblox) VALUES(?,?,?,?) "
               "ON CONFLICT(uid) DO UPDATE SET name=excluded.name, geburt=excluded.geburt, roblox=excluded.roblox",
               (uid, field_val(e, "Name"), field_val(e, "Geburtsdatum"), field_val(e, "Roblox")))
        elif kind in SCHEIN_NAMEN:
            if not db("SELECT 1 FROM ausweis WHERE uid=?", (uid,), fetch=True):
                return await i.response.send_message("Die Person hat keinen Personalausweis. Der Antrag kann nicht angenommen werden.", ephemeral=True)
            db(f"UPDATE ausweis SET {kind}=1 WHERE uid=?", (uid,))
        await i.response.edit_message(embed=review_result(e, True, i.user), view=None)
        await dm_user(i.guild, uid, f"✅ Dein Antrag ({e.title}) wurde angenommen.")
        await log(i.guild, f"{i.user.mention} hat den Antrag von <@{uid}> angenommen ({e.title}).")

    @discord.ui.button(label="Ablehnen", emoji="❌", style=discord.ButtonStyle.danger, custom_id="antrag_no")
    async def no(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_team(i.user):
            return await i.response.send_message("Nur das Team kann Anträge bearbeiten.", ephemeral=True)
        e = i.message.embeds[0]
        m = ANTRAG_RE.search(e.footer.text or "")
        if not m:
            return await i.response.send_message("Dieser Antrag ist nicht mehr gültig.", ephemeral=True)
        await i.response.send_modal(DenyModal(int(m.group(2)), e.title or "Antrag"))


class AusweisModal(discord.ui.Modal, title="Personalausweis beantragen"):
    name = discord.ui.TextInput(label="Name (Charaktername)", max_length=40)
    geburt = discord.ui.TextInput(label="Geburtsdatum", placeholder="TT.MM.JJJJ", min_length=10, max_length=10)
    roblox = discord.ui.TextInput(label="Roblox-Name", max_length=40)

    async def on_submit(self, i: discord.Interaction):
        if not GEBURT_RE.match(self.geburt.value):
            return await i.response.send_message("Bitte gib das Geburtsdatum so ein: TT.MM.JJJJ (z. B. 28.12.2007).", ephemeral=True)
        await send_request(i, "ausweis", "🪪 Personalausweis", [
            ("📛 Name", self.name.value, True), ("🎂 Geburtsdatum", self.geburt.value, True), ("🎮 Roblox", self.roblox.value, True)],
            ("ANTRAG_CHANNEL",), "Dein Antrag wurde eingereicht. Das Team prüft ihn.")


class AntragPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        custom_id="antrag_select", placeholder="Wähle eine Kategorie...",
        options=[discord.SelectOption(label=n, value=k, emoji=e, description=d) for k, n, e, d in ANTRAEGE])
    async def pick(self, i: discord.Interaction, select: discord.ui.Select):
        kind = select.values[0]
        try:
            await i.message.edit(view=AntragPanel())  # Auswahl zurücksetzen
        except discord.HTTPException:
            pass
        if kind == "ausweis":
            return await i.response.send_modal(AusweisModal())
        row = db(f"SELECT {kind} FROM ausweis WHERE uid=?", (i.user.id,), fetch=True)
        if not row:
            return await i.response.send_message("Du brauchst zuerst einen Personalausweis. Beantrage ihn über dieses Menü.", ephemeral=True)
        if row[0][0]:
            return await i.response.send_message("Diesen Schein besitzt du bereits.", ephemeral=True)
        label = next(n for k, n, _, _ in ANTRAEGE if k == kind)
        emoji = next(e for k, _, e, _ in ANTRAEGE if k == kind)
        await send_request(i, kind, f"{emoji} {label}", [], ("ANTRAG_CHANNEL",), "Dein Antrag wurde eingereicht. Das Team prüft ihn.")


class RechteModal(discord.ui.Modal, title="In-Game Rechte anfragen"):
    rb_name = discord.ui.TextInput(label="Roblox-Nutzername", max_length=40)
    rb_display = discord.ui.TextInput(label="Roblox-Anzeigename", max_length=40)
    rechte = discord.ui.TextInput(label="Gewünschte Rechte", placeholder="z. B. Teamrechte", max_length=60)
    grund = discord.ui.TextInput(label="Begründung", style=discord.TextStyle.paragraph, max_length=500)

    async def on_submit(self, i: discord.Interaction):
        await send_request(i, "rechte", "📩 Neue In-Game Rechteanfrage", [
            ("🎮 Roblox-Nutzername", self.rb_name.value, True), ("🏷️ Anzeigename", self.rb_display.value, True),
            ("🔑 Gewünschte Rechte", self.rechte.value, False), ("📝 Begründung", self.grund.value, False)],
            ("RECHTE_CHANNEL",), "Deine Anfrage wurde eingereicht. Das Team meldet sich bei dir.")


class RechteOpen(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="In-Game Rechte anfragen", emoji="📨", style=discord.ButtonStyle.success, custom_id="rechte_open")
    async def open(self, i: discord.Interaction, b: discord.ui.Button):
        if not db("SELECT 1 FROM roblox WHERE uid=?", (i.user.id,), fetch=True):
            return await i.response.send_message("Du musst im Personenverzeichnis eingetragen sein. Nutze zuerst /roblox_setzen.", ephemeral=True)
        if db("SELECT 1 FROM icsperre WHERE uid=?", (i.user.id,), fetch=True):
            return await i.response.send_message("Du hast eine IC-Rechte-Sperre und kannst keine Rechte anfragen.", ephemeral=True)
        await i.response.send_modal(RechteModal())


# ------------------------------ Aktivitätscheck ------------------------------
def acheck_embed(guild, row):
    cid, msg_id, ch_id, role_id, title, beschr, ende, status, von = row
    role = guild.get_role(role_id)
    members = [m for m in role.members if not m.bot] if role else []
    resp = {r[0] for r in db("SELECT uid FROM acheck_resp WHERE check_id=?", (cid,), fetch=True)}
    reag = [m for m in members if m.id in resp]
    offen = [m for m in members if m.id not in resp]
    aktiv = status == "aktiv"
    e = card("AKTIVITÄTSCHECK", f"{'🕐' if aktiv else '🔴'} Aktivitätscheck{'' if aktiv else ' abgelaufen'}: {title}", beschr,
             DESIGN["PRIMARY"] if aktiv else DESIGN["ERROR"], [
                 ("👥 Zielgruppe", str(len(members)), True), ("✅ Reagiert", str(len(reag)), True), ("⏳ Noch offen", str(len(offen)), True),
                 ("🎯 Zielrolle", role.mention if role else "?", True), ("🕐 Ende", f"<t:{int(ende)}:f>", True),
                 ("👤 Erstellt von", f"<@{von}>", True), ("📌 Status", "🟢 Aktiv" if aktiv else "🔴 Abgelaufen", True)],
             footer=f"{DESIGN['FOOTER']} · Check-ID {cid}")
    return e, offen


ACHECK_COLS = "id,msg_id,channel_id,role_id,title,beschr,ende,status,von"


async def finish_acheck(cid):
    rows = db(f"SELECT {ACHECK_COLS} FROM acheck WHERE id=?", (cid,), fetch=True)
    if not rows or rows[0][7] != "aktiv":
        return
    db("UPDATE acheck SET status='beendet' WHERE id=?", (cid,))
    row = list(rows[0])
    row[7] = "beendet"
    ch = bot.get_channel(row[2])
    if not ch:
        return
    e, offen = acheck_embed(ch.guild, row)
    try:
        msg = await ch.fetch_message(row[1])
        await msg.edit(embed=e, view=None)
    except discord.HTTPException:
        pass
    if offen:
        text = " ".join(m.mention for m in offen)
        await ch.send(f"⏰ **Aktivitätscheck beendet.** Nicht reagiert:\n{text[:1800]}")
    else:
        await ch.send("⏰ **Aktivitätscheck beendet.** Alle haben reagiert. 🎉")
    await log(ch.guild, f"Aktivitätscheck {cid} wurde beendet ({len(offen)} offen).")


class ACheckView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ich bin aktiv", emoji="✅", style=discord.ButtonStyle.success, custom_id="acheck_btn")
    async def btn(self, i: discord.Interaction, b: discord.ui.Button):
        rows = db(f"SELECT {ACHECK_COLS} FROM acheck WHERE msg_id=?", (i.message.id,), fetch=True)
        if not rows or rows[0][7] != "aktiv" or time.time() > rows[0][6]:
            return await i.response.send_message("Dieser Check ist bereits beendet.", ephemeral=True)
        row = rows[0]
        role = i.guild.get_role(row[3])
        if role and role not in i.user.roles:
            return await i.response.send_message("Dieser Check ist nicht für dich bestimmt.", ephemeral=True)
        db("INSERT OR IGNORE INTO acheck_resp VALUES(?,?)", (row[0], i.user.id))
        e, _ = acheck_embed(i.guild, row)
        await i.response.edit_message(embed=e)


@tasks.loop(minutes=1)
async def acheck_loop():
    for (cid,) in db("SELECT id FROM acheck WHERE status='aktiv' AND ende<=?", (time.time(),), fetch=True):
        try:
            await finish_acheck(cid)
        except Exception:
            traceback.print_exc()


@acheck_loop.before_loop
async def _acheck_before():
    await bot.wait_until_ready()


# ------------------------------ Events ------------------------------
last_dot, last_vc = {}, {}


def cooldown(store, key, seconds):
    now = time.time()
    if now - store.get(key, 0) < seconds:
        return True
    store[key] = now
    return False


@bot.event
async def setup_hook():
    for v in (VerifyView(), TicketOpen(), TicketControls(), PingRoles(), FeedbackOpen(), EinsatzView(),
              DotRequest(), AntragPanel(), ReviewView(), RechteOpen(), ACheckView(), ServerPanel()):
        bot.add_view(v)
    acheck_loop.start()
    await bot.tree.sync()


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(DESIGN["STATUS"]))
    print(f"Eingeloggt als {bot.user}")


@bot.event
async def on_member_join(m: discord.Member):
    ch = m.guild.get_channel(CFG["WELCOME_CHANNEL"])
    if ch:
        text = DESIGN["WELCOME_TEXT"].replace("{user}", m.mention).replace("{count}", str(m.guild.member_count))
        await ch.send(embed=card("WILLKOMMEN", "👋 Neues Mitglied", text, DESIGN["SUCCESS"],
                                 [("🔢 Mitglied Nr.", str(m.guild.member_count), True),
                                  ("📅 Konto erstellt", discord.utils.format_dt(m.created_at, "R"), True)],
                                 thumb=m.display_avatar.url, banner=True))
    await log(m.guild, f"{m.mention} ist beigetreten.")


@bot.event
async def on_member_remove(m: discord.Member):
    ch = m.guild.get_channel(CFG["LEAVE_CHANNEL"])
    if ch:
        await ch.send(embed=card("ABSCHIED", "🚪 Mitglied gegangen", DESIGN["LEAVE_TEXT"].replace("{name}", m.display_name),
                                 DESIGN["ERROR"], thumb=m.display_avatar.url))
    await log(m.guild, f"{m.display_name} hat den Server verlassen.")


@bot.event
async def on_member_ban(guild, user):
    await log(guild, f"{user} wurde gebannt.")


@bot.event
async def on_message_delete(msg: discord.Message):
    if msg.author.bot or not msg.guild or not msg.content:
        return
    await log(msg.guild, f"Nachricht von {msg.author.mention} in {msg.channel.mention} gelöscht:\n{msg.content[:1500]}")


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.author.bot or not before.guild or before.content == after.content:
        return
    await log(before.guild, f"{before.author.mention} hat in {before.channel.mention} eine Nachricht bearbeitet.\n"
                            f"**Vorher:** {before.content[:700]}\n**Nachher:** {after.content[:700]}")


@bot.event
async def on_message(msg: discord.Message):
    if msg.author.bot or not msg.guild:
        return
    if msg.content.strip() == "." and in_kontroll(msg.channel.id) and not cooldown(last_dot, msg.author.id, 60):
        e = card("KONTROLLE", "🛡️ Discord-Kontrolle", f"{msg.author.mention} wartet auf Kontrolle.\nEin Supporter kann annehmen oder ablehnen.",
                 DESIGN["PRIMARY"], [("👤 Mitglied", msg.author.mention, True), ("📌 Status", "🟡 Wartet", True)],
                 thumb=msg.author.display_avatar.url, footer=f"{DESIGN['FOOTER']} · KONTROLLE:{msg.author.id}")
        await msg.channel.send(embed=e, view=DotRequest())
    await bot.process_commands(msg)


@bot.event
async def on_voice_state_update(m: discord.Member, before, after):
    if m.bot:
        return
    rooms = {
        CFG["SUPPORT_VC"]: ("Support", CFG["SUPPORT_PING"]),
        CFG["HIGHTEAM_VC"]: ("Highteam", CFG["HIGHTEAM_PING"]),
        CFG["BUERO_VC"]: ("Büro", CFG["BUERO_PING"]),
    }
    if after.channel and after.channel != before.channel and after.channel.id in rooms:
        name, role_id = rooms[after.channel.id]
        if not cooldown(last_vc, m.id, 30):
            alert = m.guild.get_channel(CFG["ALERT_CHANNEL"])
            if alert:
                e = card("WARTERAUM", f"🔔 {name}-Warteraum", color=DESIGN["WARN"],
                         fields=[("👤 Wartet", m.mention, True), ("📍 Raum", name, True)], thumb=m.display_avatar.url)
                await alert.send(f"<@&{role_id}>", embed=e)
            await log(m.guild, f"{m.mention} ist dem {name}-Warteraum beigetreten.")
        try:
            if m.guild.voice_client is None:
                await after.channel.connect()
        except Exception as e:
            print("Voice-Join fehlgeschlagen:", e)
    vc = m.guild.voice_client
    if vc and len(vc.channel.members) == 1:
        await vc.disconnect()


# ------------------------------ Panels ------------------------------
@bot.tree.command(description="Verify-Panel senden")
@team_only()
async def verify_panel(i: discord.Interaction):
    await i.channel.send(embed=card("VERIFIZIERUNG", "✅ Server freischalten", DESIGN["VERIFY_TEXT"], DESIGN["SUCCESS"], banner=True), view=VerifyView())
    await i.response.send_message("Gesendet.", ephemeral=True)


@bot.tree.command(description="Ticket-Panel senden")
@team_only()
async def ticket_panel(i: discord.Interaction):
    await i.channel.send(embed=ticket_panel_card(), view=TicketOpen())
    await i.response.send_message("Gesendet.", ephemeral=True)


@bot.tree.command(description="Ping-Rollen-Panel senden")
@team_only()
async def pingrollen_panel(i: discord.Interaction):
    e = card("BENACHRICHTIGUNGEN", "🔔 Ping-Rollen", "Tippe auf einen Button, um die Rolle zu erhalten oder wieder abzugeben.\nSo bekommst du nur Pings zu Themen, die dich interessieren.", banner=True)
    await i.channel.send(embed=e, view=PingRoles())
    await i.response.send_message("Gesendet.", ephemeral=True)


@bot.tree.command(description="Feedback-Panel senden")
@team_only()
async def feedback_panel(i: discord.Interaction):
    e = card("FEEDBACK", "💜 Team-Feedback", "Lob, Kritik oder Verbesserungsvorschläge für unser Team?\nTippe auf den Button und bewerte ein Teammitglied.", DESIGN["ACCENT"], banner=True)
    await i.channel.send(embed=e, view=FeedbackOpen())
    await i.response.send_message("Gesendet.", ephemeral=True)


@bot.tree.command(description="Antragssystem-Panel senden (Ausweis, Führerschein, Waffenschein)")
@team_only()
async def antrag_panel(i: discord.Interaction):
    fields = [(f"{e} {n}", d, True) for _, n, e, d in ANTRAEGE]
    e = card("ANTRAGSSYSTEM", "🪪 Antragssystem", "Wähle unten im Menü aus, was du beantragen möchtest.\nFür Führer- und Waffenscheine brauchst du zuerst einen Personalausweis.",
             DESIGN["PRIMARY"], fields, banner=True)
    await i.channel.send(embed=e, view=AntragPanel())
    await i.response.send_message("Gesendet.", ephemeral=True)


@bot.tree.command(description="Rechte-Anfrage-Panel senden")
@team_only()
async def rechte_panel(i: discord.Interaction):
    e = card("RECHTE", "📨 In-Game Rechte anfragen", "Du musst im Personenverzeichnis eingetragen sein (/roblox_setzen).\nTippe auf den Button und fülle das Formular aus.",
             DESIGN["INFO"], banner=True)
    await i.channel.send(embed=e, view=RechteOpen())
    await i.response.send_message("Gesendet.", ephemeral=True)


@bot.tree.command(description="Serverstatus-Panel senden (Server an/aus, Modi)")
@team_only()
async def serverstatus_panel(i: discord.Interaction):
    await i.response.send_message("Panel wird gesendet.", ephemeral=True)
    msg = await i.channel.send(embed=server_embed(), view=ServerPanel())
    set_setting("panel_server", f"{i.channel.id}:{msg.id}")


@bot.tree.command(description="Automatisch aktualisierte Teamliste senden")
@team_only()
async def teamliste_panel(i: discord.Interaction):
    await i.response.send_message("Panel wird gesendet.", ephemeral=True)
    msg = await i.channel.send(embeds=team_embeds(i.guild))
    set_setting("panel_team", f"{i.channel.id}:{msg.id}")


@bot.tree.command(description="Automatisch aktualisierte Fraktionsliste senden")
@team_only()
async def fraktionsliste_panel(i: discord.Interaction):
    await i.response.send_message("Panel wird gesendet.", ephemeral=True)
    msg = await i.channel.send(embeds=fraktion_embeds(i.guild))
    set_setting("panel_fraktion", f"{i.channel.id}:{msg.id}")


@bot.tree.command(description="Eigenes Embed senden (Farbe optional als Hex, z. B. FF0000)")
@team_only()
async def embed(i: discord.Interaction, titel: str, text: str, farbe: str = ""):
    try:
        color = int(farbe.replace("#", ""), 16) if farbe else None
    except ValueError:
        return await i.response.send_message("Ungültige Farbe. Beispiel: FF0000", ephemeral=True)
    await i.channel.send(embed=card("INFO", titel, text.replace("\\n", "\n"), color))
    await i.response.send_message("Gesendet.", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat ein Embed gesendet: {titel}")


@bot.tree.command(description="Ankündigung senden (optional mit Ping)")
@team_only()
async def ankuendigung(i: discord.Interaction, titel: str, text: str, ping: discord.Role = None, kanal: discord.TextChannel = None):
    ch = kanal or i.channel
    e = card("ANKÜNDIGUNG", f"📢 {titel}", text.replace("\\n", "\n"), DESIGN["PRIMARY"], [("✍️ Von", i.user.mention, True)], banner=True)
    await ch.send(content=ping.mention if ping else None, embed=e)
    await i.response.send_message(f"Ankündigung in {ch.mention} gesendet.", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat eine Ankündigung gesendet: {titel}")


@bot.tree.command(description="Umfrage erstellen (2 bis 4 Antworten)")
@team_only()
async def umfrage(i: discord.Interaction, frage: str, antwort1: str, antwort2: str, antwort3: str = "", antwort4: str = ""):
    opts = [a for a in (antwort1, antwort2, antwort3, antwort4) if a]
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    text = "\n".join(f"{emojis[n]}  {a}" for n, a in enumerate(opts))
    await i.response.send_message(embed=card("UMFRAGE", f"📊 {frage}", text, DESIGN["ACCENT"], [("✍️ Gestartet von", i.user.mention, True)]))
    msg = await i.original_response()
    for n in range(len(opts)):
        await msg.add_reaction(emojis[n])


# ------------------------------ RP Start / Stop / Status ------------------------------
@bot.tree.command(description="RP starten")
@team_only()
async def rp_start(i: discord.Interaction, servercode: str, ping: bool = True):
    await do_rp_start(i.guild, i.user, servercode, ping)
    await i.response.send_message("RP gestartet.", ephemeral=True)


@bot.tree.command(description="RP beenden")
@team_only()
async def rp_stop(i: discord.Interaction):
    await do_rp_stop(i.guild, i.user)
    await i.response.send_message("RP beendet.", ephemeral=True)


@bot.tree.command(description="Zeigt, ob gerade RP läuft")
async def rp_status(i: discord.Interaction):
    start = get_setting("rp_start")
    if start:
        e = card("ROLEPLAY", "📡 RP läuft", color=DESIGN["SUCCESS"],
                 fields=[("📡 Status", "🟢 LIVE", True), ("🔑 Servercode", f"`{get_setting('rp_code', '?')}`", True),
                         ("⏱️ Seit", f"<t:{int(float(start))}:R>", True)])
    else:
        e = card("ROLEPLAY", "🔴 Kein RP", "Aktuell läuft keine Roleplay-Sitzung.", DESIGN["ERROR"])
    await i.response.send_message(embed=e)


# ------------------------------ Einsatz ------------------------------
@bot.tree.command(description="Einsatz melden")
@app_commands.choices(prioritaet=[app_commands.Choice(name="Niedrig", value="niedrig"),
                                  app_commands.Choice(name="Mittel", value="mittel"),
                                  app_commands.Choice(name="Hoch", value="hoch")])
@team_only()
async def einsatz(i: discord.Interaction, stichwort: str, ort: str, prioritaet: app_commands.Choice[str], details: str = "-"):
    label, color = PRIO[prioritaet.value]
    e = card("EINSATZ", f"🚨 {stichwort}", f"> {details}", color, [
        ("📍 Ort", ort, True), ("⚡ Priorität", label, True), ("📞 Gemeldet von", i.user.mention, True),
        ("🚑 Einsatzkräfte", "—", False),
    ])
    await i.response.send_message(embed=e, view=EinsatzView())
    await log(i.guild, f"{i.user.mention} hat einen Einsatz gemeldet: {stichwort} ({ort}).")


# ------------------------------ Dienst ------------------------------
@bot.tree.command(description="Dienst antreten")
@team_only()
async def dienst_an(i: discord.Interaction):
    if db("SELECT 1 FROM dienst WHERE uid=?", (i.user.id,), fetch=True):
        return await i.response.send_message("Du bist bereits im Dienst.", ephemeral=True)
    db("INSERT INTO dienst VALUES(?,?)", (i.user.id, time.time()))
    e = card("DIENST", "🟢 Dienst angetreten", color=DESIGN["SUCCESS"],
             fields=[("👤 Mitglied", i.user.mention, True), ("🕐 Seit", discord.utils.format_dt(discord.utils.utcnow(), "t"), True)])
    await i.response.send_message(embed=e)
    await log(i.guild, f"{i.user.mention} hat den Dienst angetreten.")


@bot.tree.command(description="Dienst beenden")
@team_only()
async def dienst_aus(i: discord.Interaction):
    row = db("SELECT start FROM dienst WHERE uid=?", (i.user.id,), fetch=True)
    if not row:
        return await i.response.send_message("Du bist nicht im Dienst.", ephemeral=True)
    dauer = int(time.time() - row[0][0])
    db("DELETE FROM dienst WHERE uid=?", (i.user.id,))
    db("INSERT INTO dienstzeit VALUES(?,?) ON CONFLICT(uid) DO UPDATE SET sek = sek + excluded.sek", (i.user.id, dauer))
    gesamt = db("SELECT sek FROM dienstzeit WHERE uid=?", (i.user.id,), fetch=True)[0][0]
    e = card("DIENST", "🔴 Dienst beendet", color=DESIGN["ERROR"],
             fields=[("👤 Mitglied", i.user.mention, True), ("⏱️ Diese Schicht", fmt_dur(dauer), True), ("📊 Gesamt", fmt_dur(gesamt), True)])
    await i.response.send_message(embed=e)
    await log(i.guild, f"{i.user.mention} hat den Dienst beendet ({fmt_dur(dauer)}).")


@bot.tree.command(description="Wer ist gerade im Dienst?")
@team_only()
async def dienst_liste(i: discord.Interaction):
    rows = db("SELECT uid,start FROM dienst ORDER BY start", fetch=True)
    await i.response.send_message(embed=list_card("DIENST", "🟢 Aktuell im Dienst", [f"🟢 <@{u}> seit <t:{int(s)}:R>" for u, s in rows], "Niemand ist im Dienst.", DESIGN["SUCCESS"]))


@bot.tree.command(description="Dienstzeit-Rangliste")
@team_only()
async def dienst_top(i: discord.Interaction):
    rows = db("SELECT uid,sek FROM dienstzeit ORDER BY sek DESC LIMIT 10", fetch=True)
    medals = ["🥇", "🥈", "🥉"]
    await i.response.send_message(embed=list_card("DIENST", "🏆 Dienstzeit-Rangliste", [f"{medals[n - 1] if n <= 3 else f'`{n}.`'} <@{u}> — {fmt_dur(s)}" for n, (u, s) in enumerate(rows, 1)], "Noch keine Dienstzeiten."))


# ------------------------------ Aktivitätscheck-Befehle ------------------------------
@bot.tree.command(description="Aktivitätscheck für eine Rolle starten")
@team_only()
async def aktivitaetscheck(i: discord.Interaction, rolle: discord.Role, titel: str, beschreibung: str = "Bitte bestätige, dass du aktiv bist.",
                           stunden: app_commands.Range[int, 1, 168] = 24):
    ende = time.time() + stunden * 3600
    await i.response.send_message(f"Check für {rolle.mention} wird gestartet.", ephemeral=True)
    tmp = discord.Embed(description="Wird erstellt …")
    msg = await i.channel.send(content=rolle.mention, embed=tmp, view=ACheckView())
    db("INSERT INTO acheck(msg_id,channel_id,role_id,title,beschr,ende,status,von) VALUES(?,?,?,?,?,?,?,?)",
       (msg.id, i.channel.id, rolle.id, titel, beschreibung, ende, "aktiv", i.user.id))
    row = db(f"SELECT {ACHECK_COLS} FROM acheck WHERE msg_id=?", (msg.id,), fetch=True)[0]
    e, _ = acheck_embed(i.guild, row)
    await msg.edit(embed=e)
    await log(i.guild, f"{i.user.mention} hat einen Aktivitätscheck für {rolle.name} gestartet ({stunden} Std.).")


@bot.tree.command(description="Letzten Aktivitätscheck jetzt beenden")
@team_only()
async def aktivitaetscheck_ende(i: discord.Interaction):
    row = db("SELECT id FROM acheck WHERE status='aktiv' ORDER BY id DESC LIMIT 1", fetch=True)
    if not row:
        return await i.response.send_message("Es läuft kein Aktivitätscheck.", ephemeral=True)
    await i.response.send_message("Check wird beendet.", ephemeral=True)
    await finish_acheck(row[0][0])


@bot.tree.command(description="Wer hat beim letzten Aktivitätscheck noch nicht reagiert?")
@team_only()
async def aktivitaetscheck_offen(i: discord.Interaction):
    rows = db(f"SELECT {ACHECK_COLS} FROM acheck ORDER BY id DESC LIMIT 1", fetch=True)
    if not rows:
        return await i.response.send_message("Es gab noch keinen Aktivitätscheck.", ephemeral=True)
    _, offen = acheck_embed(i.guild, rows[0])
    await i.response.send_message(embed=list_card("AKTIVITÄTSCHECK", f"⏳ Noch offen: {rows[0][4]}", [f"⏳ {m.mention}" for m in offen], "Alle haben reagiert. 🎉", DESIGN["WARN"]), ephemeral=True)


# ------------------------------ Fraktionen ------------------------------
def fraktion_log_card(title, color, name, owner, anwesen, grund, user):
    return card("FRAKTION", title, color=color, fields=[
        ("📛 Name", name, True), ("👑 Owner", owner.mention if hasattr(owner, "mention") else f"<@{owner}>", True),
        ("🏠 Anwesen", str(anwesen), True), ("📝 Grund", grund, False),
        ("✍️ Erstellt von", user.mention, True), ("📅 Datum", discord.utils.format_dt(discord.utils.utcnow(), "F"), True)])


async def send_fraktion(i, embed):
    ch = pick_channel(i.guild, "FRAKTION_CHANNEL", "TEAMLOG_CHANNEL")
    if ch and ch.id != i.channel.id:
        await ch.send(embed=embed)
        await i.response.send_message(f"Eingetragen in {ch.mention}.", ephemeral=True)
    else:
        await i.response.send_message(embed=embed)


@bot.tree.command(description="Fraktion hinzufügen")
@team_only()
async def fraktion_add(i: discord.Interaction, name: str, owner: discord.Member, anwesen: app_commands.Range[int, 0, 9999], grund: str = "-"):
    if db("SELECT 1 FROM fraktionen WHERE name=? COLLATE NOCASE", (name,), fetch=True):
        return await i.response.send_message("Diese Fraktion gibt es schon. Nutze /fraktion_edit.", ephemeral=True)
    db("INSERT INTO fraktionen VALUES(?,?,?)", (name, owner.id, anwesen))
    await send_fraktion(i, fraktion_log_card("✅ Fraktion hinzugefügt ✅", DESIGN["SUCCESS"], name, owner, anwesen, grund, i.user))
    await refresh_fraktion_panel(i.guild)
    await log(i.guild, f"{i.user.mention} hat die Fraktion {name} hinzugefügt.")


@bot.tree.command(description="Fraktion bearbeiten (Owner und/oder Anwesen)")
@team_only()
async def fraktion_edit(i: discord.Interaction, name: str, owner: discord.Member = None,
                        anwesen: app_commands.Range[int, 0, 9999] = None, grund: str = "-"):
    row = db("SELECT name,owner,anwesen FROM fraktionen WHERE name=? COLLATE NOCASE", (name,), fetch=True)
    if not row:
        return await i.response.send_message("Diese Fraktion gibt es nicht.", ephemeral=True)
    n, o, a = row[0]
    new_o = owner.id if owner else o
    new_a = anwesen if anwesen is not None else a
    db("UPDATE fraktionen SET owner=?, anwesen=? WHERE name=?", (new_o, new_a, n))
    await send_fraktion(i, fraktion_log_card("✏️ Fraktion bearbeitet ✏️", DESIGN["INFO"], n, new_o, new_a, grund, i.user))
    await refresh_fraktion_panel(i.guild)
    await log(i.guild, f"{i.user.mention} hat die Fraktion {n} bearbeitet.")


@bot.tree.command(description="Fraktion entfernen")
@team_only()
async def fraktion_remove(i: discord.Interaction, name: str, grund: str = "-"):
    row = db("SELECT name,owner,anwesen FROM fraktionen WHERE name=? COLLATE NOCASE", (name,), fetch=True)
    if not row:
        return await i.response.send_message("Diese Fraktion gibt es nicht.", ephemeral=True)
    n, o, a = row[0]
    db("DELETE FROM fraktionen WHERE name=?", (n,))
    await send_fraktion(i, fraktion_log_card("🗑️ Fraktion entfernt 🗑️", DESIGN["ERROR"], n, o, a, grund, i.user))
    await refresh_fraktion_panel(i.guild)
    await log(i.guild, f"{i.user.mention} hat die Fraktion {n} entfernt.")


@bot.tree.command(description="Alle Fraktionen anzeigen")
async def fraktionsliste(i: discord.Interaction):
    await i.response.send_message(embeds=fraktion_embeds(i.guild))


@bot.tree.command(description="Infos zu einer Fraktion")
async def fraktion_info(i: discord.Interaction, name: str):
    row = db("SELECT name,owner,anwesen FROM fraktionen WHERE name=? COLLATE NOCASE", (name,), fetch=True)
    if not row:
        return await i.response.send_message("Diese Fraktion gibt es nicht.", ephemeral=True)
    n, o, a = row[0]
    await i.response.send_message(embed=card("FRAKTION", f"🏴 {n}", color=DESIGN["PRIMARY"],
                                             fields=[("👑 Owner", f"<@{o}>", True), ("🏠 Anwesen", str(a), True)]))


# ------------------------------ Ausweis ------------------------------
async def roblox_headshot(name):
    """Holt das Roblox-Kopfbild. Gibt None zurück, wenn es nicht klappt."""
    try:
        timeout = aiohttp.ClientTimeout(total=6)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.post("https://users.roblox.com/v1/usernames/users",
                              json={"usernames": [name.lstrip("@")], "excludeBannedUsers": True}) as r:
                uid = (await r.json())["data"][0]["id"]
            url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={uid}&size=420x420&format=Png&isCircular=false"
            async with s.get(url) as r:
                return (await r.json())["data"][0]["imageUrl"]
    except Exception:
        return None


def ausweis_embed(member, row, headshot=None):
    uid, name, geburt, roblox, pkw, lkw, moto, kws, gws = row
    fs = [n for n, v in (("PKW", pkw), ("LKW", lkw), ("Motorrad", moto)) if v]
    return card("AUSWEIS", "🪪 PERSONALAUSWEIS", color=DESIGN["PRIMARY"], thumb=headshot or member.display_avatar.url, fields=[
        ("📛 Name", name, True), ("🎂 Geburtsdatum", geburt, True), ("🎮 Roblox", f"@{roblox}", True),
        ("🚗 Führerscheine", ", ".join(fs) if fs else "Keine", False),
        ("🎯 Großer Waffenschein", "✅ Ja" if gws else "❌ Nein", True),
        ("🔫 Kleiner Waffenschein", "✅ Ja" if kws else "❌ Nein", True)])


@bot.tree.command(description="Personalausweis anzeigen")
async def ausweis(i: discord.Interaction, user: discord.Member = None):
    user = user or i.user
    row = db("SELECT uid,name,geburt,roblox,pkw,lkw,moto,kws,gws FROM ausweis WHERE uid=?", (user.id,), fetch=True)
    if not row:
        return await i.response.send_message(f"{user.display_name} hat keinen Personalausweis.", ephemeral=True)
    await i.response.defer()
    head = await roblox_headshot(row[0][3])
    await i.followup.send(embed=ausweis_embed(user, row[0], head))


@bot.tree.command(description="Personalausweis löschen")
@team_only()
async def ausweis_loeschen(i: discord.Interaction, user: discord.Member, grund: str):
    db("DELETE FROM ausweis WHERE uid=?", (user.id,))
    e = team_card("🗑️ Ausweis gelöscht", DESIGN["ERROR"], [("👤 Mitglied", user.mention, True), ("🛡️ Durch", i.user.mention, True), ("📝 Grund", f"> {grund}", False)])
    await post_team(i, e, f"{i.user.mention} hat den Ausweis von {user.mention} gelöscht: {grund}")


SCHEIN_CHOICES = [app_commands.Choice(name=n, value=k) for k, n in SCHEIN_NAMEN.items()]


@bot.tree.command(description="Schein direkt vergeben (ohne Antrag)")
@app_commands.choices(schein=SCHEIN_CHOICES)
@team_only()
async def schein_geben(i: discord.Interaction, user: discord.Member, schein: app_commands.Choice[str]):
    if not db("SELECT 1 FROM ausweis WHERE uid=?", (user.id,), fetch=True):
        return await i.response.send_message("Die Person hat keinen Personalausweis.", ephemeral=True)
    db(f"UPDATE ausweis SET {schein.value}=1 WHERE uid=?", (user.id,))
    e = team_card("✅ Schein vergeben", DESIGN["SUCCESS"], [("👤 Mitglied", user.mention, True), ("🛡️ Durch", i.user.mention, True), ("📄 Schein", schein.name, True)])
    await post_team(i, e, f"{i.user.mention} hat {user.mention} den Schein {schein.name} vergeben.")


@bot.tree.command(description="Schein entziehen (Führerschein- oder Waffenschein-Entzug)")
@app_commands.choices(schein=SCHEIN_CHOICES)
@team_only()
async def schein_entziehen(i: discord.Interaction, user: discord.Member, schein: app_commands.Choice[str], grund: str):
    if not db("SELECT 1 FROM ausweis WHERE uid=?", (user.id,), fetch=True):
        return await i.response.send_message("Die Person hat keinen Personalausweis.", ephemeral=True)
    db(f"UPDATE ausweis SET {schein.value}=0 WHERE uid=?", (user.id,))
    e = team_card("🚫 Schein entzogen", DESIGN["ERROR"], [("👤 Mitglied", user.mention, True), ("🛡️ Durch", i.user.mention, True),
                                                       ("📄 Schein", schein.name, True), ("📝 Grund", f"> {grund}", False)])
    await post_team(i, e, f"{i.user.mention} hat {user.mention} den Schein {schein.name} entzogen: {grund}")


# ------------------------------ Roblox-Namen ------------------------------
@bot.tree.command(description="Deinen Roblox-Namen eintragen")
async def roblox_setzen(i: discord.Interaction, name: str):
    db("INSERT OR REPLACE INTO roblox VALUES(?,?)", (i.user.id, name))
    await i.response.send_message(f"Roblox-Name gespeichert: **{name}**", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat den Roblox-Namen {name} eingetragen.")


@bot.tree.command(description="Roblox-Namen eines Mitglieds entfernen")
@team_only()
async def roblox_entfernen(i: discord.Interaction, user: discord.Member):
    db("DELETE FROM roblox WHERE uid=?", (user.id,))
    await i.response.send_message(f"Eintrag von {user.mention} entfernt.", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat den Roblox-Eintrag von {user.mention} entfernt.")


@bot.tree.command(description="Liste Discord-Name und Roblox-Name")
async def roblox_liste(i: discord.Interaction):
    rows = db("SELECT uid,name FROM roblox ORDER BY name COLLATE NOCASE", fetch=True)
    await i.response.send_message(embed=list_card("ROBLOX", "🎮 Discord ↔ Roblox", [f"<@{u}> ➜ **{n}**" for u, n in rows], "Noch keine Einträge."))


# ------------------------------ Team ------------------------------
@bot.tree.command(description="Neues Teammitglied eintragen")
@team_only()
async def team_beitritt(i: discord.Interaction, user: discord.Member, position: discord.Role, grund: str):
    old = get_rank(user.id)
    db("INSERT OR REPLACE INTO teamrang VALUES(?,?)", (user.id, position.id))
    ok = await apply_rank(i.guild, user, old, position)
    e = team_card("👋 Team-Beitritt", DESIGN["SUCCESS"], [
        ("👤 Mitglied", user.mention, True), ("🎖️ Position", position.mention, True), ("🛡️ Durch", i.user.mention, True),
        ("📝 Grund", f"> {grund}", False)], user.display_avatar.url)
    await post_team(i, e, f"{i.user.mention} hat {user.mention} ins Team aufgenommen ({position.name}).")
    await refresh_team_panel(i.guild)
    if not ok:
        await i.followup.send("Rollen konnten nicht vergeben werden. Steht die Bot-Rolle weit genug oben?", ephemeral=True)


async def rank_change(i, user, rolle, grund, up):
    old = get_rank(user.id)
    if old is None:
        return await i.response.send_message("Diese Person ist nicht im Team. Nutze zuerst /team_beitritt.", ephemeral=True)
    db("INSERT OR REPLACE INTO teamrang VALUES(?,?)", (user.id, rolle.id))
    ok = await apply_rank(i.guild, user, old, rolle)
    old_role = i.guild.get_role(old)
    von = old_role.mention if old_role else "Unbekannt"
    title, color = ("📈 Uprank", DESIGN["SUCCESS"]) if up else ("📉 Downrank", DESIGN["WARN"])
    e = team_card(title, color, [
        ("👤 Mitglied", user.mention, True), ("🛡️ Durch", i.user.mention, True),
        ("🎖️ Rangänderung", f"{von}  ➜  {rolle.mention}", False), ("📝 Grund", f"> {grund}", False)], user.display_avatar.url)
    await post_team(i, e, f"{i.user.mention} hat {user.mention} auf {rolle.name} {'befördert' if up else 'degradiert'}.")
    await refresh_team_panel(i.guild)
    if not ok:
        await i.followup.send("Rollen konnten nicht vergeben werden. Steht die Bot-Rolle weit genug oben?", ephemeral=True)


@bot.tree.command(description="Teammitglied befördern")
@team_only()
async def uprank(i: discord.Interaction, user: discord.Member, rolle: discord.Role, grund: str):
    await rank_change(i, user, rolle, grund, True)


@bot.tree.command(description="Teammitglied degradieren")
@team_only()
async def downrank(i: discord.Interaction, user: discord.Member, rolle: discord.Role, grund: str):
    await rank_change(i, user, rolle, grund, False)


@bot.tree.command(description="Teammitglied aus dem Team entfernen")
@team_only()
async def teamkick(i: discord.Interaction, user: discord.Member, grund: str):
    old = get_rank(user.id)
    db("DELETE FROM teamrang WHERE uid=?", (user.id,))
    db("DELETE FROM dienst WHERE uid=?", (user.id,))
    ok = True
    try:
        for rid in (old, CFG["TEAM_ROLE"]):
            role = i.guild.get_role(rid) if rid else None
            if role:
                await user.remove_roles(role)
    except discord.Forbidden:
        ok = False
    e = team_card("🚪 Team-Kick", DESIGN["ERROR"], [
        ("👤 Mitglied", user.mention, True), ("🛡️ Durch", i.user.mention, True), ("📝 Grund", f"> {grund}", False)], user.display_avatar.url)
    await post_team(i, e, f"{i.user.mention} hat {user.mention} aus dem Team gekickt: {grund}")
    await refresh_team_panel(i.guild)
    if not ok:
        await i.followup.send("Rollen konnten nicht entfernt werden. Steht die Bot-Rolle weit genug oben?", ephemeral=True)


@bot.tree.command(description="Teamwarn vergeben")
@team_only()
async def teamwarn(i: discord.Interaction, user: discord.Member, grund: str):
    db("INSERT INTO warns VALUES(?,?,?)", (user.id, grund, i.user.id))
    n = len(db("SELECT 1 FROM warns WHERE uid=?", (user.id,), fetch=True))
    fields = [("👤 Mitglied", user.mention, True), ("🛡️ Durch", i.user.mention, True), ("📊 Warnungen", warn_bar(n), True)]
    if n >= DESIGN["MAX_WARNS"]:
        fields.append(("🚨 Hinweis", "Maximale Warnungen erreicht", False))
    fields.append(("📝 Grund", f"> {grund}", False))
    await post_team(i, team_card("⚠️ Team-Warn", DESIGN["WARN"], fields, user.display_avatar.url),
                    f"{i.user.mention} hat {user.mention} verwarnt (Warn {n}): {grund}")


@bot.tree.command(description="Teamwarn entfernen (Nummer aus /teamwarns)")
@team_only()
async def teamwarn_entfernen(i: discord.Interaction, user: discord.Member, nummer: int, grund: str):
    rows = db("SELECT rowid, grund FROM warns WHERE uid=? ORDER BY rowid", (user.id,), fetch=True)
    if not 1 <= nummer <= len(rows):
        return await i.response.send_message("Diese Warn-Nummer gibt es nicht. Schau mit /teamwarns nach.", ephemeral=True)
    rid, entfernt = rows[nummer - 1]
    db("DELETE FROM warns WHERE rowid=?", (rid,))
    e = team_card("🔄 Team-Warn entfernt", DESIGN["SUCCESS"], [
        ("👤 Mitglied", user.mention, True), ("🛡️ Durch", i.user.mention, True), ("📊 Warnungen", warn_bar(len(rows) - 1), True),
        ("🗑️ Entfernt", entfernt, False), ("📝 Grund", f"> {grund}", False)], user.display_avatar.url)
    await post_team(i, e, f"{i.user.mention} hat einen Teamwarn von {user.mention} entfernt: {grund}")


@bot.tree.command(description="Teamwarns eines Mitglieds anzeigen")
@team_only()
async def teamwarns(i: discord.Interaction, user: discord.Member):
    rows = db("SELECT grund,von FROM warns WHERE uid=? ORDER BY rowid", (user.id,), fetch=True)
    await i.response.send_message(embed=list_card("TEAM", f"⚠️ Teamwarns von {user.display_name}", [f"`{n}.` {g} · von <@{v}>" for n, (g, v) in enumerate(rows, 1)], "Keine Warns.", DESIGN["WARN"]))


@bot.tree.command(description="Team-Abmeldung")
@team_only()
async def abmeldung(i: discord.Interaction, bis: str, grund: str):
    db("INSERT OR REPLACE INTO abmeldungen VALUES(?,?,?)", (i.user.id, bis, grund))
    e = team_card("📅 Team-Abmeldung", DESIGN["WARN"], [
        ("👤 Mitglied", i.user.mention, True), ("📆 Bis", bis, True), ("📝 Grund", f"> {grund}", False)], i.user.display_avatar.url)
    await post_team(i, e, f"{i.user.mention} hat sich abgemeldet (bis {bis}): {grund}")


@bot.tree.command(description="Dich aus der Abmeldung zurückmelden")
@team_only()
async def rueckmeldung(i: discord.Interaction):
    db("DELETE FROM abmeldungen WHERE uid=?", (i.user.id,))
    e = team_card("✅ Team-Rückmeldung", DESIGN["SUCCESS"], [("👤 Mitglied", i.user.mention, True)], i.user.display_avatar.url)
    await post_team(i, e, f"{i.user.mention} hat sich zurückgemeldet.")


@bot.tree.command(description="Alle aktuellen Abmeldungen")
@team_only()
async def abmeldungen(i: discord.Interaction):
    rows = db("SELECT uid,bis,grund FROM abmeldungen", fetch=True)
    await i.response.send_message(embed=list_card("TEAM", "📅 Abmeldungen", [f"<@{u}> · bis **{b}** · {g}" for u, b, g in rows], "Niemand abgemeldet.", DESIGN["WARN"]))


@bot.tree.command(description="Teamliste anzeigen")
async def teamliste(i: discord.Interaction):
    await i.response.send_message(embeds=team_embeds(i.guild))


# ------------------------------ Notizen (nur Team) ------------------------------
@bot.tree.command(description="Interne Notiz zu einem Mitglied speichern")
@team_only()
async def notiz(i: discord.Interaction, user: discord.Member, text: str):
    db("INSERT INTO notizen VALUES(?,?,?,?)", (user.id, text, i.user.id, datetime.datetime.now().strftime("%d.%m.%Y")))
    await i.response.send_message(f"Notiz zu {user.mention} gespeichert.", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat eine Notiz zu {user.mention} gespeichert.")


@bot.tree.command(description="Interne Notizen eines Mitglieds anzeigen")
@team_only()
async def notizen(i: discord.Interaction, user: discord.Member):
    rows = db("SELECT text,von,zeit FROM notizen WHERE uid=? ORDER BY rowid", (user.id,), fetch=True)
    e = list_card("NOTIZEN", f"🗒️ Notizen zu {user.display_name}", [f"`{n}.` {t} · {z} · <@{v}>" for n, (t, v, z) in enumerate(rows, 1)], "Keine Notizen.")
    await i.response.send_message(embed=e, ephemeral=True)


@bot.tree.command(description="Interne Notiz löschen (Nummer aus /notizen)")
@team_only()
async def notiz_loeschen(i: discord.Interaction, user: discord.Member, nummer: int):
    rows = db("SELECT rowid FROM notizen WHERE uid=? ORDER BY rowid", (user.id,), fetch=True)
    if not 1 <= nummer <= len(rows):
        return await i.response.send_message("Diese Nummer gibt es nicht.", ephemeral=True)
    db("DELETE FROM notizen WHERE rowid=?", (rows[nummer - 1][0],))
    await i.response.send_message("Notiz gelöscht.", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat eine Notiz zu {user.mention} gelöscht.")


# ------------------------------ IC-Sperre ------------------------------
@bot.tree.command(description="IC-Rechte sperren")
@team_only()
async def ic_sperre(i: discord.Interaction, user: discord.Member, grund: str):
    db("INSERT OR REPLACE INTO icsperre VALUES(?,?)", (user.id, grund))
    e = team_card("🚫 IC-Rechte-Sperre", DESIGN["ERROR"], [
        ("👤 Mitglied", user.mention, True), ("🛡️ Durch", i.user.mention, True), ("📝 Grund", f"> {grund}", False)], user.display_avatar.url)
    await post_team(i, e, f"{i.user.mention} hat {user.mention} IC-gesperrt: {grund}")


@bot.tree.command(description="IC-Sperre aufheben")
@team_only()
async def ic_entsperren(i: discord.Interaction, user: discord.Member):
    db("DELETE FROM icsperre WHERE uid=?", (user.id,))
    e = team_card("✅ IC-Sperre aufgehoben", DESIGN["SUCCESS"], [("👤 Mitglied", user.mention, True), ("🛡️ Durch", i.user.mention, True)], user.display_avatar.url)
    await post_team(i, e, f"{i.user.mention} hat die IC-Sperre von {user.mention} aufgehoben.")


@bot.tree.command(description="Liste aller IC-Sperren")
async def ic_liste(i: discord.Interaction):
    rows = db("SELECT uid,grund FROM icsperre", fetch=True)
    await i.response.send_message(embed=list_card("IC-RECHTE", "🚫 Gesperrte Mitglieder", [f"🚫 <@{u}> · {g}" for u, g in rows], "Keine IC-Sperren.", DESIGN["ERROR"]))


# ------------------------------ Häuser ------------------------------
@bot.tree.command(description="Haus hinzufügen oder Besitzer ändern")
@team_only()
async def haus_setzen(i: discord.Interaction, name: str, besitzer: discord.Member):
    db("INSERT OR REPLACE INTO houses VALUES(?,?)", (name, besitzer.id))
    e = card("HÄUSER", "🏠 Haus vergeben", color=DESIGN["SUCCESS"],
             fields=[("🏠 Haus", name, True), ("👑 Besitzer", besitzer.mention, True), ("🛡️ Durch", i.user.mention, True)])
    await i.response.send_message(embed=e)
    await log(i.guild, f"{i.user.mention} hat Haus {name} an {besitzer.mention} vergeben.")


@bot.tree.command(description="Haus entfernen")
@team_only()
async def haus_loeschen(i: discord.Interaction, name: str):
    db("DELETE FROM houses WHERE name=?", (name,))
    await i.response.send_message(embed=card("HÄUSER", "🏠 Haus entfernt", f"**{name}** wurde entfernt.", DESIGN["WARN"]))
    await log(i.guild, f"{i.user.mention} hat Haus {name} entfernt.")


@bot.tree.command(description="Häuserliste")
async def haeuser(i: discord.Interaction):
    rows = db("SELECT name,besitzer FROM houses ORDER BY name COLLATE NOCASE", fetch=True)
    await i.response.send_message(embed=list_card("HÄUSER", "🏘️ Häuserliste", [f"🏠 **{n}** ➜ <@{b}>" for n, b in rows], "Keine Häuser eingetragen."))


@bot.tree.command(description="Häuser eines Mitglieds anzeigen")
async def haus_von(i: discord.Interaction, user: discord.Member):
    rows = db("SELECT name FROM houses WHERE besitzer=? ORDER BY name COLLATE NOCASE", (user.id,), fetch=True)
    await i.response.send_message(embed=list_card("HÄUSER", f"🏠 Häuser von {user.display_name}", [f"🏠 {n[0]}" for n in rows], "Besitzt keine Häuser."))


# ------------------------------ Moderation ------------------------------
@bot.tree.command(description="Mitglied kicken")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i: discord.Interaction, user: discord.Member, grund: str):
    try:
        await user.kick(reason=grund)
    except discord.Forbidden:
        return await i.response.send_message("Dafür fehlen mir Rechte. Steht die Bot-Rolle weit genug oben?", ephemeral=True)
    e = card("MODERATION", "🚪 Kick", color=DESIGN["ERROR"], fields=[("👤 Mitglied", user.mention, True), ("🛡️ Durch", i.user.mention, True), ("📝 Grund", f"> {grund}", False)])
    await i.response.send_message(embed=e)
    await log(i.guild, f"{i.user.mention} hat {user.mention} gekickt: {grund}")


@bot.tree.command(description="Mitglied bannen")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i: discord.Interaction, user: discord.Member, grund: str):
    try:
        await user.ban(reason=grund)
    except discord.Forbidden:
        return await i.response.send_message("Dafür fehlen mir Rechte. Steht die Bot-Rolle weit genug oben?", ephemeral=True)
    e = card("MODERATION", "🔨 Ban", color=DESIGN["ERROR"], fields=[("👤 Mitglied", str(user), True), ("🛡️ Durch", i.user.mention, True), ("📝 Grund", f"> {grund}", False)])
    await i.response.send_message(embed=e)
    await log(i.guild, f"{i.user.mention} hat {user.mention} gebannt: {grund}")


@bot.tree.command(description="Bann aufheben (mit Nutzer-ID)")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(i: discord.Interaction, nutzer_id: str, grund: str = "-"):
    try:
        await i.guild.unban(discord.Object(id=int(nutzer_id)), reason=grund)
    except ValueError:
        return await i.response.send_message("Das ist keine gültige ID.", ephemeral=True)
    except discord.NotFound:
        return await i.response.send_message("Diese Person ist nicht gebannt.", ephemeral=True)
    except discord.Forbidden:
        return await i.response.send_message("Dafür fehlen mir Rechte.", ephemeral=True)
    e = card("MODERATION", "🔓 Entbannt", color=DESIGN["SUCCESS"], fields=[("🆔 Nutzer-ID", nutzer_id, True), ("🛡️ Durch", i.user.mention, True), ("📝 Grund", f"> {grund}", False)])
    await i.response.send_message(embed=e)
    await log(i.guild, f"{i.user.mention} hat {nutzer_id} entbannt: {grund}")


@bot.tree.command(description="Mitglied stummschalten (Timeout in Minuten)")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(i: discord.Interaction, user: discord.Member, minuten: app_commands.Range[int, 1, 40320], grund: str):
    try:
        await user.timeout(datetime.timedelta(minutes=minuten), reason=grund)
    except discord.Forbidden:
        return await i.response.send_message("Dafür fehlen mir Rechte. Steht die Bot-Rolle weit genug oben?", ephemeral=True)
    e = card("MODERATION", "🔇 Timeout", color=DESIGN["WARN"], fields=[("👤 Mitglied", user.mention, True), ("⏱️ Dauer", f"{minuten} Min.", True), ("📝 Grund", f"> {grund}", False)])
    await i.response.send_message(embed=e)
    await log(i.guild, f"{i.user.mention} hat {user.mention} für {minuten} Min. stummgeschaltet: {grund}")


@bot.tree.command(description="Timeout aufheben")
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(i: discord.Interaction, user: discord.Member):
    try:
        await user.timeout(None)
    except discord.Forbidden:
        return await i.response.send_message("Dafür fehlen mir Rechte.", ephemeral=True)
    await i.response.send_message(embed=card("MODERATION", "🔊 Timeout aufgehoben", f"{user.mention} darf wieder schreiben.", DESIGN["SUCCESS"]))
    await log(i.guild, f"{i.user.mention} hat den Timeout von {user.mention} aufgehoben.")


@bot.tree.command(description="Mitglied verwarnen")
@team_only()
async def warn(i: discord.Interaction, user: discord.Member, grund: str):
    db("INSERT INTO mwarns VALUES(?,?,?,?)", (user.id, grund, i.user.id, datetime.datetime.now().strftime("%d.%m.%Y")))
    n = len(db("SELECT 1 FROM mwarns WHERE uid=?", (user.id,), fetch=True))
    e = card("MODERATION", "⚠️ Verwarnung", color=DESIGN["WARN"], thumb=user.display_avatar.url,
             fields=[("👤 Mitglied", user.mention, True), ("🔢 Verwarnung Nr.", str(n), True), ("🛡️ Durch", i.user.mention, True), ("📝 Grund", f"> {grund}", False)])
    await i.response.send_message(embed=e)
    await log(i.guild, f"{i.user.mention} hat {user.mention} verwarnt (Warn {n}): {grund}")


@bot.tree.command(description="Verwarnungen eines Mitglieds anzeigen")
@team_only()
async def warns(i: discord.Interaction, user: discord.Member):
    rows = db("SELECT grund,von,zeit FROM mwarns WHERE uid=?", (user.id,), fetch=True)
    await i.response.send_message(embed=list_card("MODERATION", f"⚠️ Verwarnungen von {user.display_name}", [f"`{n}.` {g} · {z} · <@{v}>" for n, (g, v, z) in enumerate(rows, 1)], "Keine Verwarnungen.", DESIGN["WARN"]))


@bot.tree.command(description="Nachrichten im Channel löschen")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(i: discord.Interaction, anzahl: app_commands.Range[int, 1, 100]):
    await i.response.defer(ephemeral=True)
    deleted = await i.channel.purge(limit=anzahl)
    await i.followup.send(f"{len(deleted)} Nachrichten gelöscht.", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat {len(deleted)} Nachrichten in {i.channel.mention} gelöscht.")


@bot.tree.command(description="Channel sperren (niemand kann schreiben)")
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=False)
    await i.response.send_message(embed=card("MODERATION", "🔒 Channel gesperrt", "Hier kann gerade niemand schreiben.", DESIGN["ERROR"]))
    await log(i.guild, f"{i.user.mention} hat {i.channel.mention} gesperrt.")


@bot.tree.command(description="Channel entsperren")
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=None)
    await i.response.send_message(embed=card("MODERATION", "🔓 Channel entsperrt", "Schreiben ist wieder möglich.", DESIGN["SUCCESS"]))
    await log(i.guild, f"{i.user.mention} hat {i.channel.mention} entsperrt.")


@bot.tree.command(description="Slowmode im Channel setzen (0 = aus)")
@app_commands.checks.has_permissions(manage_channels=True)
async def slowmode(i: discord.Interaction, sekunden: app_commands.Range[int, 0, 21600]):
    await i.channel.edit(slowmode_delay=sekunden)
    await i.response.send_message(f"Slowmode: {sekunden} Sekunden." if sekunden else "Slowmode ist aus.", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat den Slowmode in {i.channel.mention} auf {sekunden}s gesetzt.")


@bot.tree.command(description="Rolle an ein Mitglied vergeben")
@app_commands.checks.has_permissions(manage_roles=True)
async def rolle_geben(i: discord.Interaction, user: discord.Member, rolle: discord.Role):
    if rolle >= i.user.top_role and not i.user.guild_permissions.administrator:
        return await i.response.send_message("Diese Rolle ist nicht niedriger als deine höchste Rolle.", ephemeral=True)
    try:
        await user.add_roles(rolle)
    except discord.Forbidden:
        return await i.response.send_message("Dafür fehlen mir Rechte. Steht die Bot-Rolle weit genug oben?", ephemeral=True)
    await i.response.send_message(f"{rolle.mention} an {user.mention} vergeben.", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat {user.mention} die Rolle {rolle.name} gegeben.")


@bot.tree.command(description="Rolle von einem Mitglied entfernen")
@app_commands.checks.has_permissions(manage_roles=True)
async def rolle_nehmen(i: discord.Interaction, user: discord.Member, rolle: discord.Role):
    if rolle >= i.user.top_role and not i.user.guild_permissions.administrator:
        return await i.response.send_message("Diese Rolle ist nicht niedriger als deine höchste Rolle.", ephemeral=True)
    try:
        await user.remove_roles(rolle)
    except discord.Forbidden:
        return await i.response.send_message("Dafür fehlen mir Rechte. Steht die Bot-Rolle weit genug oben?", ephemeral=True)
    await i.response.send_message(f"{rolle.mention} von {user.mention} entfernt.", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat {user.mention} die Rolle {rolle.name} entzogen.")


# ------------------------------ Ticket-Werkzeuge ------------------------------
@bot.tree.command(description="Person zu diesem Ticket hinzufügen")
@team_only()
async def ticket_hinzufuegen(i: discord.Interaction, user: discord.Member):
    if not (i.channel.topic or "").startswith("ticket:"):
        return await i.response.send_message("Das geht nur in einem Ticket-Channel.", ephemeral=True)
    await i.channel.set_permissions(user, view_channel=True, send_messages=True)
    await i.response.send_message(embed=card("TICKET", "➕ Person hinzugefügt", f"{user.mention} wurde zum Ticket hinzugefügt.", DESIGN["SUCCESS"], footer=DESIGN["FOOTER_TICKET"]))
    await log(i.guild, f"{i.user.mention} hat {user.mention} zu {i.channel.mention} hinzugefügt.")


@bot.tree.command(description="Person aus diesem Ticket entfernen")
@team_only()
async def ticket_entfernen(i: discord.Interaction, user: discord.Member):
    if not (i.channel.topic or "").startswith("ticket:"):
        return await i.response.send_message("Das geht nur in einem Ticket-Channel.", ephemeral=True)
    await i.channel.set_permissions(user, overwrite=None)
    await i.response.send_message(embed=card("TICKET", "➖ Person entfernt", f"{user.mention} wurde aus dem Ticket entfernt.", DESIGN["WARN"], footer=DESIGN["FOOTER_TICKET"]))
    await log(i.guild, f"{i.user.mention} hat {user.mention} aus {i.channel.mention} entfernt.")


# ------------------------------ Info ------------------------------
@bot.tree.command(description="Infos über ein Mitglied")
async def userinfo(i: discord.Interaction, user: discord.Member):
    rb = db("SELECT name FROM roblox WHERE uid=?", (user.id,), fetch=True)
    rid = get_rank(user.id)
    role = i.guild.get_role(rid) if rid else None
    ic = db("SELECT grund FROM icsperre WHERE uid=?", (user.id,), fetch=True)
    w = len(db("SELECT 1 FROM mwarns WHERE uid=?", (user.id,), fetch=True))
    dz = db("SELECT sek FROM dienstzeit WHERE uid=?", (user.id,), fetch=True)
    ausw = db("SELECT name FROM ausweis WHERE uid=?", (user.id,), fetch=True)
    e = card("PROFIL", f"👤 {user.display_name}", thumb=user.display_avatar.url, fields=[
        ("🎮 Roblox", rb[0][0] if rb else "nicht eingetragen", True),
        ("🎖️ Team", role.mention if role else "kein Teammitglied", True),
        ("🚫 IC-Sperre", ic[0][0] if ic else "keine", True),
        ("⚠️ Verwarnungen", str(w), True),
        ("⏱️ Dienstzeit", fmt_dur(dz[0][0]) if dz else "–", True),
        ("🪪 Ausweis", ausw[0][0] if ausw else "keiner", True),
        ("📅 Beigetreten", discord.utils.format_dt(user.joined_at, "D") if user.joined_at else "?", True),
    ])
    await i.response.send_message(embed=e)


@bot.tree.command(description="Profilbild eines Mitglieds anzeigen")
async def avatar(i: discord.Interaction, user: discord.Member = None):
    user = user or i.user
    await i.response.send_message(embed=card("PROFIL", f"🖼️ {user.display_name}", image=user.display_avatar.url))


@bot.tree.command(description="Infos über den Server")
async def serverinfo(i: discord.Interaction):
    g = i.guild
    e = card("SERVER", f"🏙️ {g.name}", thumb=g.icon.url if g.icon else None, fields=[
        ("👥 Mitglieder", str(g.member_count), True),
        ("💬 Channels", str(len(g.channels)), True),
        ("🎖️ Rollen", str(len(g.roles)), True),
        ("📅 Erstellt", discord.utils.format_dt(g.created_at, "D"), True),
        ("🚀 Boosts", str(g.premium_subscription_count), True),
        ("👑 Besitzer", g.owner.mention if g.owner else "?", True),
    ])
    await i.response.send_message(embed=e)


@bot.tree.command(description="Zeigt die Reaktionszeit des Bots")
async def ping(i: discord.Interaction):
    up = fmt_dur(time.time() - START_TIME)
    e = card("BOT", "🏓 Pong", color=DESIGN["SUCCESS"], fields=[("📶 Latenz", f"{round(bot.latency * 1000)} ms", True), ("⏱️ Läuft seit", up, True)])
    await i.response.send_message(embed=e, ephemeral=True)


@bot.tree.command(description="Alle Befehle anzeigen")
async def hilfe(i: discord.Interaction):
    e = card("HILFE", "📖 Befehlsübersicht", fields=[
        ("👥 Für alle", "`/ausweis` `/roblox_setzen` `/roblox_liste` `/teamliste` `/fraktionsliste` `/fraktion_info` `/ic_liste` `/haeuser` `/haus_von` `/rp_status` `/userinfo` `/avatar` `/serverinfo` `/ping` `/hilfe`", False),
        ("🎖️ Team: Verwaltung", "`/team_beitritt` `/uprank` `/downrank` `/teamkick` `/teamwarn` `/teamwarn_entfernen` `/teamwarns` `/abmeldung` `/rueckmeldung` `/abmeldungen` `/notiz` `/notizen` `/notiz_loeschen`", False),
        ("🚨 Team: Betrieb", "`/rp_start` `/rp_stop` `/einsatz` `/dienst_an` `/dienst_aus` `/dienst_liste` `/dienst_top` `/aktivitaetscheck` `/aktivitaetscheck_ende` `/aktivitaetscheck_offen` `/ankuendigung` `/umfrage` `/embed`", False),
        ("🏴 Team: Fraktionen & Scheine", "`/fraktion_add` `/fraktion_edit` `/fraktion_remove` `/ausweis_loeschen` `/schein_geben` `/schein_entziehen` `/ic_sperre` `/ic_entsperren` `/haus_setzen` `/haus_loeschen`", False),
        ("🎫 Tickets", "`/ticket_hinzufuegen` `/ticket_entfernen`", False),
        ("🔨 Moderation", "`/warn` `/warns` `/kick` `/ban` `/unban` `/timeout` `/untimeout` `/clear` `/lock` `/unlock` `/slowmode` `/rolle_geben` `/rolle_nehmen`", False),
        ("🧩 Panels", "`/verify_panel` `/ticket_panel` `/pingrollen_panel` `/feedback_panel` `/antrag_panel` `/rechte_panel` `/serverstatus_panel` `/teamliste_panel` `/fraktionsliste_panel`", False),
        ("🎨 Design & Panels (ohne Code)", "`/panel_neu` `/design_setzen` `/design_anzeigen` `/design_zuruecksetzen` `/config_setzen` `/config_anzeigen` `/config_zuruecksetzen`\nNachricht gedrückt halten → **Apps**: Panel bearbeiten, In Panel umwandeln, Feld hinzufügen/entfernen, Kopf & Fuß", False),
    ])
    await i.response.send_message(embed=e, ephemeral=True)


# ------------------------------ Panel-Editor & Einstellungen (alles direkt in Discord) ------------------------------
HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")
TRUE_WORDS = ("ja", "j", "yes", "y", "1", "true")
AUTO_AUTHOR_ENDINGS = (" · ANTRAG", " · EINSATZ", " · AKTIVITÄTSCHECK", " · KONTROLLE")


def parse_color(text):
    t = text.strip()
    if not HEX_RE.match(t):
        raise ValueError("Farbe")
    return int(t.lstrip("#"), 16)


def hex_of(color):
    return f"{color.value:06X}" if color is not None else f"{DESIGN['PRIMARY']:06X}"


def clean_url(u):
    u = (u or "").strip()
    return u if u.lower().startswith(("http://", "https://")) else None


def panel_error(message):
    """Gibt einen Fehlertext zurück, wenn die Nachricht nicht bearbeitet werden darf."""
    if message.author.id != bot.user.id:
        return "Das ist keine Nachricht vom Bot. Nutze „In Panel umwandeln“, um daraus ein Panel zu machen."
    if not message.embeds:
        return "Diese Nachricht hat kein Panel (Embed)."
    e = message.embeds[0]
    author = (e.author.name or "").upper()
    footer = e.footer.text or ""
    if author.endswith(AUTO_AUTHOR_ENDINGS) or "ANTRAG:" in footer or "KONTROLLE:" in footer:
        return "Diese Nachricht wird vom Bot automatisch verwaltet und kann nicht bearbeitet werden."
    return None


class SafeModal(discord.ui.Modal):
    async def on_error(self, i: discord.Interaction, error: Exception):
        traceback.print_exception(type(error), error, error.__traceback__)
        msg = "Das hat nicht geklappt. Prüfe deine Eingaben (Farbe als Hex wie E53935, Bild-Links mit https://)."
        if i.response.is_done():
            await i.followup.send(msg, ephemeral=True)
        else:
            await i.response.send_message(msg, ephemeral=True)


async def save_embed(message, embed):
    embeds = list(message.embeds)
    embeds[0] = embed
    await message.edit(embeds=embeds)


class PanelEditModal(SafeModal, title="Panel bearbeiten"):
    def __init__(self, message):
        super().__init__()
        self.message = message
        e = message.embeds[0]
        self.titel = discord.ui.TextInput(label="Titel", default=(e.title or "")[:256], required=False, max_length=256)
        self.text = discord.ui.TextInput(label="Text", style=discord.TextStyle.paragraph,
                                         default=(e.description or "")[:4000], required=False, max_length=4000)
        self.farbe = discord.ui.TextInput(label="Farbe (Hex, z. B. E53935)", default=hex_of(e.color), required=False, max_length=7)
        self.bild = discord.ui.TextInput(label="Großes Bild (Link)", default=(e.image.url or "")[:500], required=False, max_length=500)
        self.thumb = discord.ui.TextInput(label="Kleines Bild rechts (Link)", default=(e.thumbnail.url or "")[:500], required=False, max_length=500)
        for item in (self.titel, self.text, self.farbe, self.bild, self.thumb):
            self.add_item(item)

    async def on_submit(self, i: discord.Interaction):
        e = self.message.embeds[0]
        if self.farbe.value.strip():
            try:
                e.color = discord.Color(parse_color(self.farbe.value))
            except ValueError:
                return await i.response.send_message("Ungültige Farbe. Beispiel: E53935", ephemeral=True)
        for val, setter in ((self.bild.value, e.set_image), (self.thumb.value, e.set_thumbnail)):
            v = val.strip()
            if v and not clean_url(v):
                return await i.response.send_message("Bild-Links müssen mit https:// beginnen.", ephemeral=True)
            setter(url=v or None)
        e.title = self.titel.value or None
        e.description = self.text.value or None
        await save_embed(self.message, e)
        await i.response.send_message("Panel aktualisiert ✅", ephemeral=True)
        await log(i.guild, f"{i.user.mention} hat ein Panel bearbeitet: {self.message.jump_url}")


class PanelHeadModal(SafeModal, title="Kopfzeile & Fußzeile"):
    def __init__(self, message):
        super().__init__()
        self.message = message
        e = message.embeds[0]
        self.kopf = discord.ui.TextInput(label="Kopfzeile oben (leer = ausblenden)", default=(e.author.name or "")[:256], required=False, max_length=256)
        self.fuss = discord.ui.TextInput(label="Fußzeile unten (leer = ausblenden)", default=(e.footer.text or "")[:300], required=False, max_length=300)
        self.add_item(self.kopf)
        self.add_item(self.fuss)

    async def on_submit(self, i: discord.Interaction):
        e = self.message.embeds[0]
        kopf, fuss = self.kopf.value.strip(), self.fuss.value.strip()
        if kopf:
            e.set_author(name=kopf, icon_url=e.author.icon_url)
        else:
            e.remove_author()
        if fuss:
            e.set_footer(text=fuss, icon_url=e.footer.icon_url)
        else:
            e.remove_footer()
        await save_embed(self.message, e)
        await i.response.send_message("Kopf- und Fußzeile aktualisiert ✅", ephemeral=True)


class PanelFieldModal(SafeModal, title="Feld hinzufügen"):
    name = discord.ui.TextInput(label="Titel des Feldes", max_length=256)
    wert = discord.ui.TextInput(label="Inhalt", style=discord.TextStyle.paragraph, max_length=1024)
    inline = discord.ui.TextInput(label="Nebeneinander anzeigen? (ja/nein)", default="ja", max_length=4)

    def __init__(self, message):
        super().__init__()
        self.message = message

    async def on_submit(self, i: discord.Interaction):
        e = self.message.embeds[0]
        if len(e.fields) >= 25:
            return await i.response.send_message("Ein Panel kann höchstens 25 Felder haben.", ephemeral=True)
        e.add_field(name=self.name.value, value=self.wert.value, inline=self.inline.value.strip().lower() in TRUE_WORDS)
        await save_embed(self.message, e)
        await i.response.send_message("Feld hinzugefügt ✅", ephemeral=True)


class FieldRemoveView(discord.ui.View):
    def __init__(self, message):
        super().__init__(timeout=120)
        self.message = message
        opts = [discord.SelectOption(label=f"{n + 1}. {f.name}"[:100], value=str(n))
                for n, f in enumerate(message.embeds[0].fields[:25])]
        self.sel = discord.ui.Select(placeholder="Welches Feld entfernen?", options=opts)
        self.sel.callback = self.on_pick
        self.add_item(self.sel)

    async def on_pick(self, i: discord.Interaction):
        idx = int(self.sel.values[0])
        msg = await self.message.channel.fetch_message(self.message.id)
        e = msg.embeds[0]
        if idx >= len(e.fields):
            return await i.response.edit_message(content="Das Feld gibt es nicht mehr.", view=None)
        e.remove_field(idx)
        await save_embed(msg, e)
        await i.response.edit_message(content="Feld entfernt ✅", view=None)


class PanelCreateModal(SafeModal, title="Neues Panel"):
    def __init__(self, channel, source=None):
        super().__init__()
        self.channel = channel
        self.source = source
        self.titel = discord.ui.TextInput(label="Titel", required=False, max_length=256)
        self.text = discord.ui.TextInput(label="Text", style=discord.TextStyle.paragraph, required=False, max_length=4000,
                                         default=((source.content or "")[:4000] or None) if source else None)
        self.farbe = discord.ui.TextInput(label="Farbe (Hex, z. B. E53935)", default=f"{DESIGN['PRIMARY']:06X}", required=False, max_length=7)
        self.bild = discord.ui.TextInput(label="Großes Bild (Link, optional)", required=False, max_length=500)
        self.fuss = discord.ui.TextInput(label="Fußzeile (optional)", required=False, max_length=300)
        for item in (self.titel, self.text, self.farbe, self.bild, self.fuss):
            self.add_item(item)

    async def on_submit(self, i: discord.Interaction):
        if not self.titel.value.strip() and not self.text.value.strip():
            return await i.response.send_message("Bitte gib mindestens einen Titel oder einen Text ein.", ephemeral=True)
        try:
            color = parse_color(self.farbe.value) if self.farbe.value.strip() else DESIGN["PRIMARY"]
        except ValueError:
            return await i.response.send_message("Ungültige Farbe. Beispiel: E53935", ephemeral=True)
        bild = self.bild.value.strip()
        if bild and not clean_url(bild):
            return await i.response.send_message("Bild-Links müssen mit https:// beginnen.", ephemeral=True)
        e = card("PANEL", self.titel.value.strip() or None, self.text.value, color, image=bild or None,
                 footer=self.fuss.value.strip() or None)
        await self.channel.send(embed=e)
        note = ""
        if self.source is not None and self.source.author.id == i.user.id:
            try:
                await self.source.delete()
                note = " Deine ursprüngliche Nachricht wurde gelöscht."
            except discord.HTTPException:
                pass
        await i.response.send_message(
            f"Panel in {self.channel.mention} gesendet ✅{note}\nZum Bearbeiten: Nachricht gedrückt halten → **Apps** → **Panel bearbeiten**.",
            ephemeral=True)
        await log(i.guild, f"{i.user.mention} hat ein Panel in {self.channel.mention} erstellt.")


@bot.tree.command(description="Neues Panel erstellen (Formular, ohne Code)")
@team_only()
async def panel_neu(i: discord.Interaction, kanal: discord.TextChannel = None):
    await i.response.send_modal(PanelCreateModal(kanal or i.channel))


@bot.tree.context_menu(name="Panel bearbeiten")
async def ctx_panel_edit(i: discord.Interaction, message: discord.Message):
    if not is_team(i.user):
        return await i.response.send_message("Nur das Team kann Panels bearbeiten.", ephemeral=True)
    err = panel_error(message)
    if err:
        return await i.response.send_message(err, ephemeral=True)
    await i.response.send_modal(PanelEditModal(message))


@bot.tree.context_menu(name="In Panel umwandeln")
async def ctx_panel_convert(i: discord.Interaction, message: discord.Message):
    if not is_team(i.user):
        return await i.response.send_message("Nur das Team kann Panels erstellen.", ephemeral=True)
    if not message.content:
        return await i.response.send_message("Diese Nachricht hat keinen Text.", ephemeral=True)
    await i.response.send_modal(PanelCreateModal(i.channel, message))


@bot.tree.context_menu(name="Panel: Feld hinzufügen")
async def ctx_panel_field_add(i: discord.Interaction, message: discord.Message):
    if not is_team(i.user):
        return await i.response.send_message("Nur das Team kann Panels bearbeiten.", ephemeral=True)
    err = panel_error(message)
    if err:
        return await i.response.send_message(err, ephemeral=True)
    await i.response.send_modal(PanelFieldModal(message))


@bot.tree.context_menu(name="Panel: Feld entfernen")
async def ctx_panel_field_remove(i: discord.Interaction, message: discord.Message):
    if not is_team(i.user):
        return await i.response.send_message("Nur das Team kann Panels bearbeiten.", ephemeral=True)
    err = panel_error(message)
    if err:
        return await i.response.send_message(err, ephemeral=True)
    if not message.embeds[0].fields:
        return await i.response.send_message("Dieses Panel hat keine Felder.", ephemeral=True)
    await i.response.send_message("Wähle das Feld, das entfernt werden soll:", view=FieldRemoveView(message), ephemeral=True)


@bot.tree.context_menu(name="Panel: Kopf & Fuß")
async def ctx_panel_head(i: discord.Interaction, message: discord.Message):
    if not is_team(i.user):
        return await i.response.send_message("Nur das Team kann Panels bearbeiten.", ephemeral=True)
    err = panel_error(message)
    if err:
        return await i.response.send_message(err, ephemeral=True)
    await i.response.send_modal(PanelHeadModal(message))


# ---- Design (Farben, Texte, Bilder) ----
DESIGN_NAMEN = {
    "PRIMARY": "Hauptfarbe", "SUCCESS": "Farbe Erfolg (grün)", "ERROR": "Farbe Fehler (dunkelrot)",
    "WARN": "Farbe Warnung (orange)", "NEUTRAL": "Farbe Logs (grau)", "ACCENT": "Farbe Akzent (lila)", "INFO": "Farbe Info (blau)",
    "BRAND": "Name in der Kopfzeile", "ICON": "Emoji in der Kopfzeile", "FOOTER": "Fußzeile (allgemein)",
    "FOOTER_TEAM": "Fußzeile Team", "FOOTER_TICKET": "Fußzeile Tickets", "STATUS": "Bot-Status (Spielt ...)",
    "WELCOME_TEXT": "Willkommenstext", "LEAVE_TEXT": "Text beim Verlassen", "VERIFY_TEXT": "Verify-Text (neue Panels)",
    "BANNER": "Banner-Bild unter Panels (Link)", "LOGO": "Logo neben der Kopfzeile (Link)", "MAX_WARNS": "Max. Teamwarns",
}
DESIGN_CHOICES = [app_commands.Choice(name=v, value=k) for k, v in DESIGN_NAMEN.items()]


def design_show(k):
    v = DESIGN[k]
    if k in COLOR_KEYS:
        return f"#{v:06X}"
    return str(v)[:90] or "—"


@bot.tree.command(description="Design ändern: Farben, Texte, Banner (ohne Code)")
@app_commands.choices(einstellung=DESIGN_CHOICES)
@app_commands.checks.has_permissions(administrator=True)
async def design_setzen(i: discord.Interaction, einstellung: app_commands.Choice[str], wert: str):
    k = einstellung.value
    wert = wert.strip()
    try:
        if k in COLOR_KEYS:
            DESIGN[k] = parse_color(wert)
            store = f"{DESIGN[k]:06X}"
        elif k == "MAX_WARNS":
            n = int(wert)
            if not 1 <= n <= 10:
                raise ValueError
            DESIGN[k] = n
            store = str(n)
        elif k in ("BANNER", "LOGO"):
            if wert.lower() in ("aus", "-", "leer"):
                DESIGN[k] = store = ""
            elif clean_url(wert):
                DESIGN[k] = store = wert
            else:
                raise ValueError
        else:
            if not wert:
                raise ValueError
            DESIGN[k] = store = wert
    except ValueError:
        hint = {"MAX_WARNS": "Eine Zahl von 1 bis 10.", "BANNER": "Ein Link mit https:// oder „aus“.", "LOGO": "Ein Link mit https:// oder „aus“."}.get(
            k, "Eine Farbe als Hex-Code, z. B. E53935." if k in COLOR_KEYS else "Der Text darf nicht leer sein.")
        return await i.response.send_message(f"Ungültiger Wert. {hint}", ephemeral=True)
    set_setting("design:" + k, store)
    if k == "STATUS":
        await bot.change_presence(activity=discord.Game(DESIGN["STATUS"]))
    extra = "\nPlatzhalter: `{user}` und `{count}`" if k == "WELCOME_TEXT" else ("\nPlatzhalter: `{name}`" if k == "LEAVE_TEXT" else "")
    e = card("DESIGN", "🎨 Design aktualisiert", color=DESIGN["SUCCESS"] if k not in COLOR_KEYS else DESIGN[k],
             desc="Gilt ab sofort für neue Nachrichten. Bereits gesendete Panels änderst du mit **Panel bearbeiten**." + extra,
             fields=[("Einstellung", DESIGN_NAMEN[k], True), ("Neuer Wert", design_show(k) or "—", True)])
    await i.response.send_message(embed=e, ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat das Design geändert: {DESIGN_NAMEN[k]}.")


@bot.tree.command(description="Alle Design-Einstellungen anzeigen")
@team_only()
async def design_anzeigen(i: discord.Interaction):
    lines = []
    for k, label in DESIGN_NAMEN.items():
        mark = "✏️" if get_setting("design:" + k) is not None else "▫️"
        lines.append(f"{mark} **{label}**: `{design_show(k)}`")
    await i.response.send_message(embed=card("DESIGN", "🎨 Design-Einstellungen", "\n".join(lines) + "\n\n✏️ = in Discord geändert", DESIGN["PRIMARY"]), ephemeral=True)


@bot.tree.command(description="Design-Einstellung auf den Standard zurücksetzen")
@app_commands.choices(einstellung=DESIGN_CHOICES)
@app_commands.checks.has_permissions(administrator=True)
async def design_zuruecksetzen(i: discord.Interaction, einstellung: app_commands.Choice[str]):
    k = einstellung.value
    db("DELETE FROM settings WHERE key=?", ("design:" + k,))
    DESIGN[k] = DEFAULT_DESIGN[k]
    if k == "STATUS":
        await bot.change_presence(activity=discord.Game(DESIGN["STATUS"]))
    await i.response.send_message(f"**{DESIGN_NAMEN[k]}** ist wieder auf dem Standardwert: `{design_show(k)}`", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat {DESIGN_NAMEN[k]} zurückgesetzt.")


# ---- Channel- und Rollen-IDs ----
def cfg_fmt(k, v):
    if not v:
        return "—"
    return f"<@&{v}>" if k.endswith(("_ROLE", "_PING")) else f"<#{v}>"


async def cfg_autocomplete(i: discord.Interaction, current: str):
    return [app_commands.Choice(name=k, value=k) for k in CFG if current.lower() in k.lower()][:25]


@bot.tree.command(description="Channel oder Rolle des Bots einstellen (ohne Code)")
@app_commands.checks.has_permissions(administrator=True)
async def config_setzen(i: discord.Interaction, schluessel: str,
                        kanal: Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel] = None,
                        rolle: discord.Role = None):
    k = schluessel.strip().upper()
    if k not in CFG:
        return await i.response.send_message("Diesen Schlüssel gibt es nicht. Wähle einen aus der Vorschlagsliste.", ephemeral=True)
    needs_role = k.endswith(("_ROLE", "_PING"))
    obj = rolle if needs_role else kanal
    if obj is None:
        return await i.response.send_message(f"Für **{k}** brauchst du {'eine Rolle (Feld „rolle“)' if needs_role else 'einen Channel (Feld „kanal“)'}.", ephemeral=True)
    CFG[k] = obj.id
    set_setting("cfg:" + k, obj.id)
    await i.response.send_message(embed=card("EINSTELLUNG", "✅ Gespeichert", color=DESIGN["SUCCESS"],
                                             fields=[("Schlüssel", k, True), ("Neuer Wert", cfg_fmt(k, obj.id), True)]), ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat {k} geändert: {cfg_fmt(k, obj.id)}")


config_setzen.autocomplete("schluessel")(cfg_autocomplete)


@bot.tree.command(description="Einstellung auf den Wert aus dem Code zurücksetzen")
@app_commands.checks.has_permissions(administrator=True)
async def config_zuruecksetzen(i: discord.Interaction, schluessel: str):
    k = schluessel.strip().upper()
    if k not in CFG:
        return await i.response.send_message("Diesen Schlüssel gibt es nicht.", ephemeral=True)
    db("DELETE FROM settings WHERE key=?", ("cfg:" + k,))
    CFG[k] = DEFAULT_CFG[k]
    await i.response.send_message(f"**{k}** ist wieder auf dem Wert aus dem Code: {cfg_fmt(k, CFG[k])}", ephemeral=True)
    await log(i.guild, f"{i.user.mention} hat {k} zurückgesetzt.")


config_zuruecksetzen.autocomplete("schluessel")(cfg_autocomplete)


@bot.tree.command(description="Alle Channel- und Rollen-Einstellungen anzeigen")
@team_only()
async def config_anzeigen(i: discord.Interaction):
    lines = [f"{'✏️' if get_setting('cfg:' + k) is not None else '▫️'} `{k}` ➜ {cfg_fmt(k, v)}" for k, v in CFG.items()]
    await i.response.send_message(embed=card("EINSTELLUNG", "⚙️ Channel & Rollen", "\n".join(lines) + "\n\n✏️ = in Discord geändert", DESIGN["PRIMARY"]), ephemeral=True)


bot.run(TOKEN)
