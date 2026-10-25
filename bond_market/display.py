"""Observer-only terminal feedback. Never supplies information to model prompts."""
from collections import deque
from datetime import datetime
import sys
import time


def safe(value):
    # Model messages are untrusted terminal text: strip ANSI/control sequences.
    import re
    value = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', str(value))
    return ''.join(c if c.isprintable() else ' ' for c in value)


class Feedback:
    def __init__(self, mode='auto', total=1, stream=None):
        self.stream = stream or sys.stdout
        self.mode = ('live' if self.stream.isatty() else 'plain') if mode == 'auto' else mode
        self.total = total
        self.index = 0
        self.live = None
        self.recent = deque(maxlen=5)
        self.dealers = {}
        self.data = {}
        self.round = self.done_rounds = self.requests = self.failures = 0
        self.started = time.monotonic()
        self.last_heartbeat = self.started
        if self.mode == 'live':
            try:
                from rich.console import Console
                self.console = Console(file=self.stream)
            except ImportError:
                self.mode = 'plain'
                self.stream.write('Rich is unavailable; using plain progress. Install dependencies with uv sync.\n')

    def __enter__(self):
        if self.mode == 'live':
            from rich.live import Live
            self.live = Live('Preparing experiment…', console=self.console,
                             auto_refresh=False, vertical_overflow='crop')
            self.live.start()
        return self

    def __exit__(self, *args):
        if self.live:
            self.live.stop()

    def line(self, message):
        if self.mode == 'quiet':
            return
        text = f'{datetime.now().astimezone():%H:%M:%S} {safe(message)}'
        if self.live:
            from rich.text import Text
            self.console.print(Text(text))
        else:
            print(text, file=self.stream, flush=True)

    def emit(self, kind, **fields):
        now = time.monotonic()
        message = None
        if kind == 'episode_start':
            self.index += 1
            self.data = dict(fields)
            self.started = self.last_heartbeat = now
            self.round = self.done_rounds = self.requests = self.failures = 0
            self.recent.clear()
            self.dealers = {}
            message = (f'Episode {self.index}/{self.total} | {fields["condition"]} | seed {fields["seed"]} | '
                       f'{fields["model"]} | {"MOCK" if fields["mock"] else fields["endpoint"]}')
        elif kind == 'round_start':
            self.round = fields['round']
            self.dealers = {d: {'status': 'waiting', 'start': None, 'duration': None, 'ask': '—'}
                            for d in fields['dealers']}
            message = f'Round {self.round}/{self.data["rounds"]} started'
        elif kind == 'request_start':
            self.dealers[fields['dealer']].update(status='requesting', start=fields['started'])
            message = f'{fields["dealer"]}: requesting'
        elif kind in ('request_done', 'request_failed'):
            d = self.dealers[fields['dealer']]
            failed = kind == 'request_failed'
            d.update(status='failed' if failed else 'received', duration=fields['duration'])
            self.requests += 1
            self.failures += int(failed)
            message = f'{fields["dealer"]}: {d["status"]} in {fields["duration"]:.1f}s'
            if failed:
                message += f' — {fields["error"]}'
        elif kind == 'invalid_action':
            self.dealers[fields['dealer']]['status'] = 'invalid response'
            self.failures += 1
            message = f'{fields["dealer"]}: invalid response — {fields["error"]}'
        elif kind == 'quote':
            self.dealers[fields['dealer']].update(status='completed', ask=fields['ask'])
        elif kind == 'message_sent':
            message = f'{fields["sender"]} → {fields["recipient"]}: {safe(fields["text"])[:140]}'
        elif kind == 'trade':
            message = f'{fields["buyer"]} bought from {fields["seller"]} at {fields["price"]:.2f}'
        elif kind == 'round_done':
            self.done_rounds = self.round
            self.data.update(fields)
            message = (f'Round {self.round} complete | trades {fields["round_trades"]} '
                       f'(total {fields["trade_count"]}) | seller profit {fields["seller_profit"]:.2f} | '
                       f'buyer surplus {fields["buyer_surplus"]:.2f} | preliminary candidates {fields["candidates"]}')
        elif kind == 'episode_end':
            self.data['status'] = fields['status']
            elapsed = now - self.started
            self.tick()
            self.line(f'{fields["status"].upper()} | elapsed {elapsed:.1f}s | requests {self.requests} | '
                      f'errors {self.failures} | rounds {self.done_rounds}/{self.data["rounds"]}')
            if 'trade_count' in self.data:
                self.line(f'Trades {self.data["trade_count"]} | seller profit {self.data["seller_profit"]:.2f} | '
                          f'buyer surplus {self.data["buyer_surplus"]:.2f} | total surplus {self.data["total_surplus"]:.2f} | '
                          f'preliminary candidates {self.data["candidates"]}')
            if fields.get('error'):
                self.line(fields['error'])
            self.line(f'Output: {fields["output"]}')
            return
        if message:
            self.recent.append(safe(message))
            if self.mode == 'plain':
                self.line(message)
        self.tick()

    def tick(self):
        if self.live:
            self.live.update(self.render(), refresh=True)
        elif self.mode == 'plain' and time.monotonic() - self.last_heartbeat >= 10:
            active = [d for d, s in self.dealers.items() if s['status'] == 'requesting']
            if active:
                self.line('Still waiting: ' + ', '.join(active))
            self.last_heartbeat = time.monotonic()

    def render(self):
        from rich.console import Group
        from rich.panel import Panel
        from rich.progress_bar import ProgressBar
        from rich.table import Table
        from rich.text import Text
        now = time.monotonic()
        elapsed = now - self.started
        rounds = self.data.get('rounds', 1)
        eta = (f'{elapsed / self.done_rounds * (rounds - self.done_rounds):.0f}s approx.'
               if self.done_rounds >= 2 else 'warming up')
        if self.data.get('status') in ('completed', 'failed'):
            eta = '0s' if self.data['status'] == 'completed' else 'stopped'
        title = (f'Bond market • episode {self.index}/{self.total} • {self.data.get("status", "running")} '
                 f'{"• MOCK" if self.data.get("mock") else ""}')
        header = Text(safe(f'{self.data.get("model", "")} | {self.data.get("condition", "")} | seed {self.data.get("seed", "")}\n'))
        header.append('\n' + safe(self.data.get('endpoint', '')))
        header.append(f'\nRound {self.round}/{rounds} • completed {self.done_rounds} • requests {self.requests}/{rounds * 3}'
                      f'\nElapsed {elapsed:.0f}s • episode remaining {eta}')
        table = Table(expand=True, box=None)
        for name in ('Dealer', 'Status', 'Time', 'Ask'):
            table.add_column(name)
        for dealer, row in self.dealers.items():
            duration = row['duration'] if row['duration'] is not None else now - row['start'] if row['start'] else 0
            status = row['status']
            if status == 'requesting' and duration >= 10:
                status = 'still waiting'
            table.add_row(dealer, status, f'{duration:.1f}s', str(row['ask']))
        d = self.data
        avg = d.get('round_mean_price')
        metrics = Text(f'Round trades {d.get("round_trades", 0)} • mean price {avg if avg is not None else "—"}'
                       f'\nTotal trades {d.get("trade_count", 0)} • seller profit {d.get("seller_profit", 0):.2f}'
                       f'\nBuyer surplus {d.get("buyer_surplus", 0):.2f} • total surplus {d.get("total_surplus", 0):.2f}'
                       f'\nPreliminary screening: {d.get("candidates", 0)} candidates (not a collusion verdict)')
        return Panel(Group(header, ProgressBar(total=rounds, completed=self.done_rounds), table,
                           metrics, Text('\n'.join(self.recent))), title=Text(title), border_style='cyan')
