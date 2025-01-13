import requests
from bs4 import BeautifulSoup

class R6Tracker:
    def __init__(self):
        self.base_url = "https://r6.tracker.network/r6siege/profile/ubi/"
        self.psn_url = "https://r6.tracker.network/r6siege/profile/psn/"
        self.xbox_url = "https://r6.tracker.network/r6siege/profile/xbl/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def fetch_user_data(self, username, endpoint="overview"):
        try:
            url = f"{self.base_url}{username}/{endpoint}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                try:
                    url = f"{self.psn_url}{username}/{endpoint}"
                    response = requests.get(url, headers=self.headers)
                    response.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    if response.status_code == 404:
                        url = f"{self.xbox_url}{username}/{endpoint}"
                        response = requests.get(url, headers=self.headers)
                        response.raise_for_status()
                    else:
                        raise e
            else:
                raise e
        
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup
    
    def get_stats(self, username):
        overview_soup = self.fetch_user_data(username, "overview")
        season_soup = self.fetch_user_data(username, "seasons")
        stats = {}

        # Get current season rank and points
        # find rank (帶顏色的span)
        rank_span = overview_soup.find('span', 
            attrs={
                'data-v-ca2b3935': '',
                'class': 'truncate',
                'style': lambda value: value and 'color:' in value.lower()
            })
        
        # find points
        points_span = overview_soup.find('span', 
            attrs={
                'data-v-ca2b3935': '',
                'class': 'rank-points text-20'
            })
        
        if rank_span:
            stats['rank'] = rank_span.text.strip()
        else:
            stats['rank'] = 'N/A'

        if points_span:
            stats['points'] = points_span.text.strip()
        else:
            stats['points'] = 'N/A'

        # Get best rank stats
        best_rank_span = overview_soup.find('div', class_="playlist-summary grid gap-2 items-center relative rank-table__season-summary").find('span', class_='truncate')
            
        if not best_rank_span:
            return None
            
        # 找到包含這個span的row
        row = self.find_parent_row(best_rank_span)
        if not row:
            return None
        
        stats['best_season'] =  best_rank_span.text.strip()
        
        # 找段位圖片
        rank_img = row.find('img', class_='rank-image')
        if rank_img and rank_img.get('alt'):
            stats['best_rank'] = rank_img['alt']
        
        # 找分數
        points_span = row.find('span', class_='rank-points')
        if points_span:
            stats['best_points'] = points_span.text.strip()
        
        # 找所有td
        tds = row.find_all('div', class_='stat-table__td')
        
        # 從第二個td找K/D
        if len(tds) > 1:
            kd_span = tds[1].find('span', attrs={'data-v-b50d5aea': ''})

            percentile = tds[1].find('span', class_='percentile-text')
            if percentile:
                stats['kdpercentile'] = percentile.text.strip()

                if kd_span:
                    kd_string = kd_span.text.strip().replace(percentile.text.strip(), '')
                    stats['kd'] = kd_string
            else:
                stats['kd'] = kd_span.text.strip()
            
        # 從第三個td找場次和百分比
        if len(tds) > 2:
            # 分別找場次數和百分比
            matches_val = tds[2].find('span', 
                attrs={'data-v-b50d5aea': ''}, 
                recursive=False)  # 只在直接子元素中查找
            
            percentile = tds[2].find('span', class_='percentile-text')
            if percentile:
                stats['matchpercentile'] = percentile.text.strip()

                if matches_val:
                    matches_string = matches_val.text.strip().replace(percentile.text.strip(), '')
                    stats['matches'] = matches_string
            else:
                stats['matches'] = matches_val.text.strip()
        

        # Get current season all playlist stats
        # 找到包含所有播放清單統計的表格
        tbody = overview_soup.find('div', class_='tbody')
        if not tbody:
            return None
        
        playlist_stats = []
        
        # 找到所有行
        rows = tbody.find_all('div', class_='trow')
        for row in rows:
            # 找出這一行所有的td
            cells = row.find_all('div', class_='tc')
            
            if len(cells) >= 3:  # 確保有足夠的單元格
                # 在每個td中找到最內層的span（包含實際數據）
                mode_span = cells[0].find('span', attrs={'data-v-b50d5aea': ''})
                kd_span = cells[1].find('span', attrs={'data-v-b50d5aea': ''})
                winrate_span = cells[2].find('span', attrs={'data-v-b50d5aea': ''})
                
                if mode_span and kd_span and winrate_span:  # 確保所有數據都存在
                    row_data = {
                        'playlist': mode_span.text.strip(),
                        'kd_': kd_span.text.strip(),
                        'winrate': winrate_span.text.strip()
                    }
                    playlist_stats.append(row_data)

        stats['playlist_stats'] = playlist_stats

        # Get player profile picture
        pic = overview_soup.find('img', class_='user-avatar__image').get('src')
        
        # Get player platform
        platform = overview_soup.find('svg', class_='platform-icon')
        stats['platform'] = platform['class'][1].replace('platform-', '')
        
        # Get player level
        level = overview_soup.find('span', class_='text-primary')
        stats['level'] = level.text.strip()

        # SEASON
        self.season_stats(season_soup)

        return stats, pic
    
    def season_stats(self, season_soup):
        season_data = []
        all_season = season_soup.find_all('span', attrs={
                                        'data-v-b50d5aea': '',
                                        'data-v-d258d5b0': '',
                                        'class': 'stat-value'})
        
        # 0~10是一個season的資料
        for idx, i in enumerate(all_season):
            if idx%10 == 0:
                season_var = i.text
            elif idx%10 == 1:
                kd_var = i.text
            elif idx%10 == 2:
                winrate_var = i.text
            elif idx%10 == 3:
                matches_var = i.text
            elif idx%10 == 4:
                wins_var = i.text
            elif idx%10 == 5:
                losses_var = i.text
            elif idx%10 == 6:
                avgkills_var = i.text
            elif idx%10 == 7:
                kills_var = i.text
            elif idx%10 == 8:
                deaths_var = i.text
            else:
                abandons_var = i.text
            if idx == 9:
                break
            season_data.append(i.text)
        print(season_data)
        # return season_data

    def find_parent_row(self, element):
        """找到元素所在的row"""
        current = element
        while current and not ('trow' in current.get('class', [])):
            current = current.parent
        return current

def track_main(username):
    tracker = R6Tracker()
    stats, pic = tracker.get_stats(username)
    print(stats)
    
    return stats, pic

if __name__ == "__main__":
    id = input()
    stats, pic = track_main(username=id)
