import coloredlogs, logging
import asyncio
import nest_asyncio
import telegram.error
from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import Application, CommandHandler, InlineQueryHandler, Updater, ContextTypes

logging.basicConfig(level=logging.INFO)

debug_mode = True

nest_asyncio.apply()

#Log settings
log = logging.getLogger(__name__)

fieldstyle = {'asctime': {'color': 'green'},
              'levelname': {'bold': True, 'color': 'black'},
              'filename':{'color':'cyan'},
              'funcName':{'color':'magenta'}}

levelstyles = {'critical': {'bold': True, 'color': 'red'},
               'debug': {'color': 'green'},
               'error': {'color': 'red'},
               'info': {'color':'white'},
               'warning': {'color': 'yellow'}}

coloredlogs.install(level=logging.INFO,
                    logger=log,
                    fmt='%(asctime)s [%(levelname)s] - [%(filename)s > %(funcName)s() > %(lineno)s] - %(message)s',
                    datefmt=' %Y/%m/%d %H:%M:%S',
                    field_styles=fieldstyle,
                    level_styles=levelstyles
                    )

loggingfile = logging.FileHandler("logs.log")
fileformat = logging.Formatter("%(asctime)s [%(levelname)s] - [%(filename)s > %(funcName)s() > %(lineno)s] - %(message)s")
loggingfile.setFormatter(fileformat)

loggingfile.setStream(open('logs.log', 'a', encoding='utf-8'))

log.addHandler(loggingfile)

admin_id = 6325066796

async def on_startup(application: Application):
    # Esegui qui le azioni desiderate
    log.warning("Bot avviato, eseguendo azioni di setup...")

    # Puoi inviare un messaggio a un determinato chat ID, ad esempio l'amministratore

    try:
        await application.bot.send_message(chat_id=admin_id, text="Il bot è stato avviato correttamente!")
        log.warning(f"Messaggio inviato all'amministratore (chat_id={admin_id}).")
    except Exception as e:
        log.error(f"Errore nell'inviare il messaggio di avvio: {e}")

    # Esegui altre azioni, come il controllo delle risorse del Raspberry Pi
    log.info("Azioni all'avvio completate.")

async def handleStart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if debug_mode:
        log.info('Bot started from %s', update.message.from_user)

    chat_id = update.effective_chat.id

    if update.message.chat_id == admin_id:
        # Avvia il task di monitoraggio delle risorse
        log.warning('Bot started from Admin %s', update.message.from_user)
        await update.message.reply_text(f"Comando Start ricevuto da Amministratore: {update.message.from_user.first_name} - @{update.message.from_user.username}")
    else:
        log.warning('Someone tried to start the bot, but has no permissions.')
        await update.message.reply_text("Non hai il permesso di utilizzare questo Bot.")
        pass

async def handleStopClashBot(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if debug_mode:
        log.warning('Clash bot stop command received from %s', update.message.from_user)

    masterbot_id = 1

    try:
        if update.message.chat_id == admin_id or update.message.chat_id == masterbot_id:
            log.warning('Bot Stopped from Admin %s', update.message.from_user)
            await update.message.reply_text(f"Comando STOP ricevuto da Amministratore:\n{update.message.from_user.first_name} - @{update.message.from_user.username}")
        else:
            log.warning('Someone tried to stop our clash bot: %s', update.message.from_user)
            application = Application.builder().token("7358465268:AAGKH1-vglyFjQEt4Hk6D8PZDaB2ceMXZNU").build()
            await application.bot.send_message(chat_id=admin_id, text=f'Someone tried to stop the bot: {update.message.from_user}')
            await update.message.reply_text("Non hai il permesso di utilizzare questo Bot.")
            pass
    except telegram.error.BadRequest:
        log.error(f"Errore durante l'invio del messaggio: {e}")
        application = Application.builder().token("7358465268:AAGKH1-vglyFjQEt4Hk6D8PZDaB2ceMXZNU").build()
        await application.bot.send_message(chat_id=admin_id, text=f'Errore durante l\'invio del messaggio: {e}')


async def main():
    if debug_mode:
        log.warning('DEBUG MODE ENABLED')
        application = Application.builder().token("7358465268:AAGKH1-vglyFjQEt4Hk6D8PZDaB2ceMXZNU").build()
    else:
        log.warning('Bot started on production token')
        application = Application.builder().token("7358465268:AAGKH1-vglyFjQEt4Hk6D8PZDaB2ceMXZNU").build()


    # Add command handler
    application.add_handler(CommandHandler('start', handleStart))
    application.add_handler(CommandHandler('stopclashbot1', handleStopClashBot))

    #Esegue operazioni preliminari di avvio
    await on_startup(application)

    # Start the Bot
    await application.run_polling()

if __name__ == "__main__":
    # Check if the event loop is already running
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except RuntimeError as e:
        if str(e) == "This event loop is already running":
            # If the event loop is already running, run the main function using `loop.create_task`
            loop = asyncio.get_running_loop()
            loop.create_task(main())
        else:
            raise
