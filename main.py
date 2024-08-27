import esek
from threading import Thread

if __name__ == '__main__':
    flask_thread = Thread(target=esek.start_flask)
    flask_thread.start()

    esek.run_bot()