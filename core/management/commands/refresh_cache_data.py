from django.core.management.base import BaseCommand
from core.utils.fetcher import clear_all_pickles, load_or_fetch_stock_data  # 這是你自訂的函式
from core.constants import load_sp500_symbols

class Command(BaseCommand):
    help = '清除所有快取並重新抓取股票資料'

    def handle(self, *args, **kwargs):
        self.stdout.write('📦 開始清除快取與重新抓取資料...')
        clear_all_pickles()
        load_or_fetch_stock_data(load_sp500_symbols())
        self.stdout.write(self.style.SUCCESS('✅ 所有資料已更新完畢！'))