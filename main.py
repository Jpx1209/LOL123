import sys
import locale


if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import os
os.environ["CONGHIEU"] = "utf-8"


from arsbot_ui import ArsBotUI

if __name__ == "__main__":
    app = ArsBotUI()
    app.mainloop()