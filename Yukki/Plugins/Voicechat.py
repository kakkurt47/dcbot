import asyncio
import os
import shutil
import subprocess
from sys import version as pyver

from pyrogram import Client, filters
from pyrogram.types import (InlineKeyboardMarkup, InputMediaPhoto, Message,
                            Voice)

from config import get_queue
from Yukki import SUDOERS, app, db_mem, random_assistant
from Yukki.Database import (get_active_chats, get_active_video_chats,
                            get_assistant, is_active_chat, save_assistant)
from Yukki.Decorators.checker import checker, checkerCB
from Yukki.Inline import primary_markup,choose_markup
from Yukki.Utilities.assistant import get_assistant_details

loop = asyncio.get_event_loop()

__MODULE__ = "Join/Leave"
__HELP__ = """

**Not:**
Sadece Sudo Kullanıcıları İçin


/joinassistant [Sohbet Kullanıcı Adı veya Sohbet Kimliği]
- Gruba yardımcı katılma.


/leaveassistant [Sohbet Kullanıcı Adı veya Sohbet Kimliği]
- Asistan belirli bir gruptan ayrılacak.


/leavebot [Sohbet Kullanıcı Adı veya Sohbet Kimliği]
- Bot belirli bir sohbeti terk edecek.
"""

@app.on_callback_query(filters.regex("gback_list_chose_stream"))
async def gback_list_chose_stream(_, CallbackQuery):
    await CallbackQuery.answer()
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    videoid, duration, user_id = callback_request.split("|")
    if CallbackQuery.from_user.id != int(user_id):
        return await CallbackQuery.answer(
            "Bu senin için değil! Kendi Şarkınızı Arayın.", show_alert=True
        )
    buttons = choose_markup(videoid, duration, user_id)
    await CallbackQuery.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@app.on_callback_query(filters.regex("pr_go_back_timer"))
async def pr_go_back_timer(_, CallbackQuery):
    await CallbackQuery.answer()
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    videoid, user_id = callback_request.split("|")
    if await is_active_chat(CallbackQuery.message.chat.id):
        if db_mem[CallbackQuery.message.chat.id]["videoid"] == videoid:
            dur_left = db_mem[CallbackQuery.message.chat.id]["left"]
            duration_min = db_mem[CallbackQuery.message.chat.id]["total"]
            buttons = primary_markup(videoid, user_id, dur_left, duration_min)
            await CallbackQuery.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(buttons)
            )


@app.on_callback_query(filters.regex("timer_checkup_markup"))
async def timer_checkup_markup(_, CallbackQuery):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    videoid, user_id = callback_request.split("|")
    if await is_active_chat(CallbackQuery.message.chat.id):
        if db_mem[CallbackQuery.message.chat.id]["videoid"] == videoid:
            dur_left = db_mem[CallbackQuery.message.chat.id]["left"]
            duration_min = db_mem[CallbackQuery.message.chat.id]["total"]
            return await CallbackQuery.answer(
                f"Kalan {dur_left} out of {duration_min} Dakika.",
                show_alert=True,
            )
        return await CallbackQuery.answer(f"Yürütemiyor.", show_alert=True)
    else:
        return await CallbackQuery.answer(
            f"Etkin Sesli Sohbet Yok", show_alert=True
        )


@app.on_message(filters.command("queue"))
async def activevc(_, message: Message):
    global get_queue
    if await is_active_chat(message.chat.id):
        mystic = await message.reply_text("Please Wait... Getting Queue..")
        dur_left = db_mem[message.chat.id]["left"]
        duration_min = db_mem[message.chat.id]["total"]
        got_queue = get_queue.get(message.chat.id)
        if not got_queue:
            await mystic.edit(f"Kuyrukta Hiçbir Şey Yok")
        fetched = []
        for get in got_queue:
            fetched.append(get)

        ### Results
        current_playing = fetched[0][0]
        user_name = fetched[0][1]

        msg = "**Kuyruğa Atılmış Liste**\n\n"
        msg += "**Şu Anda Yürüten:**"
        msg += "\n▶️" + current_playing[:30]
        msg += f"\n   ╚By:- {user_name}"
        msg += f"\n   ╚Duration:- Kalan `{dur_left}` dışında `{duration_min}` Dakika."
        fetched.pop(0)
        if fetched:
            msg += "\n\n"
            msg += "**Sıradaki Yukarı:**"
            getirilen şarkı için:
                name = song[0][:30]
                usr = song[1]
                dur = song[2]
                msg += f"\n⏸️{name}"
                msg += f"\n   ╠Süresi : {dur}"
                msg += f"\n   ╚Talep eden : {usr}\n"
        if len(msg) > 4096:
            await mystic.delete()
            filename = "queue.txt"
            with open(filename, "w+", encoding="utf8") as out_file:
                out_file.write(str(msg.strip()))
            await message.reply_document(
                document=filename,
                caption=f"**OUTPUT:**\n\n`Kuyruğa Atılmış Liste`",
                quote=False,
            )
            os.remove(filename)
        else:
            await mystic.edit(msg)
    else:
        await message.reply_text(f"Kuyrukta Hiçbir Şey Yok")


@app.on_message(filters.command("activevc") & filters.user(SUDOERS))
async def activevc(_, message: Message):
    served_chats = []
    try:
        chats = await get_active_chats()
        for chat in chats:
            served_chats.append(int(chat["chat_id"]))
    except Exception as e:
        await message.reply_text(f"**Error:-** {e}")
    text = ""
    j = 0
    for x in served_chats:
        try:
            title = (await app.get_chat(x)).title
        except Exception:
            title = "Private Group"
        if (await app.get_chat(x)).username:
            user = (await app.get_chat(x)).username
            text += (
                f"<b>{j + 1}.</b>  [{title}](https://t.me/{user})[`{x}`]\n"
            )
        else:
            text += f"<b>{j + 1}. {title}</b> [`{x}`]\n"
        j += 1
    if not text:
        await message.reply_text("No Active Voice Chats")
    else:
        await message.reply_text(
            f"**Active Voice Chats:-**\n\n{text}",
            disable_web_page_preview=True,
        )


@app.on_message(filters.command("activevideo") & filters.user(SUDOERS))
async def activevi_(_, message: Message):
    served_chats = []
    try:
        chats = await get_active_video_chats()
        for chat in chats:
            served_chats.append(int(chat["chat_id"]))
    except Exception as e:
        await message.reply_text(f"**Error:-** {e}")
    text = ""
    j = 0
    for x in served_chats:
        try:
            title = (await app.get_chat(x)).title
        except Exception:
            title = "Private Group"
        if (await app.get_chat(x)).username:
            user = (await app.get_chat(x)).username
            text += (
                f"<b>{j + 1}.</b>  [{title}](https://t.me/{user})[`{x}`]\n"
            )
        else:
            text += f"<b>{j + 1}. {title}</b> [`{x}`]\n"
        j += 1
    if not text:
        await message.reply_text("Etkin Sesli Sohbet Yok")
    else:
        await message.reply_text(
            f"**Active Video Calls:-**\n\n{text}",
            disable_web_page_preview=True,
        )


@app.on_message(filters.command("joinassistant") & filters.user(SUDOERS))
async def basffy(_, message):
    if len(message.command) != 2:
        await message.reply_text(
            "**Kullanım:**\n/joinassistant [Sohbet Kullanıcı Adı veya Sohbet Kimliği]"
        )
        return
    chat = message.text.split(None, 2)[1]
    try:
        chat_id = (await app.get_chat(chat)).id
    except:
        return await message.reply_text(
            "Add Bot to this Chat First.. Unknown Chat for the bot"
        )
    _assistant = await get_assistant(chat_id, "assistant")
    if not _assistant:
        return await message.reply_text(
            "Önceden Kaydedilmiş Yardımcı Bulunamadı.\n\nAsistan'ı /oynat yapın {Chat}'s Groupta"
        )
    else:
        ran_ass = _assistant["saveassistant"]
    ASS_ID, ASS_NAME, ASS_USERNAME, ASS_ACC = await get_assistant_details(
        ran_ass
    )
    try:
        await ASS_ACC.join_chat(chat_id)
    except Exception as e:
        await message.reply_text(f"Failed\n**Possible reason could be**:{e}")
        return
    await message.reply_text("Joined.")


@app.on_message(filters.command("leavebot") & filters.user(SUDOERS))
async def baaaf(_, message):
    if len(message.command) != 2:
        await message.reply_text(
            "**Usage:**\n/leavebot [Chat Username or Chat ID]"
        )
        return
    chat = message.text.split(None, 2)[1]
    try:
        await app.leave_chat(chat)
    except Exception as e:
        await message.reply_text(f"Failed\n**Possible reason could be**:{e}")
        print(e)
        return
    await message.reply_text("Bot has left the chat successfully")


@app.on_message(filters.command("leaveassistant") & filters.user(SUDOERS))
async def baujaf(_, message):
    if len(message.command) != 2:
        await message.reply_text(
            "**Usage:**\n/leave [Sohbet Kullanıcı Adı veya Sohbet Kimliği]"
        )
        return
    chat = message.text.split(None, 2)[1]
    try:
        chat_id = (await app.get_chat(chat)).id
    except:
        return await message.reply_text(
            "Önce Bu Sohbete Bot Ekle.. Bot için Bilinmeyen Sohbet"
        )
    _assistant = await get_assistant(chat, "assistant")
    if not _assistant:
        return await message.reply_text(
            "Önceden Kaydedilmiş Yardımcı Bulunamadı.\n\nAsistan'ı /play inside üzerinden ayarlayabilirsiniz {Chat}'s Group"
        )
    else:
        ran_ass = _assistant["saveassistant"]
    ASS_ID, ASS_NAME, ASS_USERNAME, ASS_ACC = await get_assistant_details(
        ran_ass
    )
    try:
        await ASS_ACC.leave_chat(chat_id)
    except Exception as e:
        await message.reply_text(f"Başarısız\n**Olası neden**:{e}")
        return
    await message.reply_text("Left.")