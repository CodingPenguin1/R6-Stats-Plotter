import asyncio
import csv
import json
from os import mkdir

import matplotlib.pyplot as plt
import r6sapi as api

from Player import Player

players = []


def get_stats(usernames, email, password):
    async def _download(usernames, email, password):
        global players

        auth = api.Auth(email, password)
        api_players = await auth.get_player_batch(usernames, api.Platforms.UPLAY)
        for api_player in api_players:
            player = Player(api_player.name, await api_player.get_all_operators())
            players.append(player)

            season = -1
            while True:
                try:
                    player.rank = await api_player.get_rank('cus', season)
                    if season == -1:
                        player.rank_name = player.rank.get_rank_name()
                    mmr = int(player.rank.max_mmr)
                    player.mmr_history.append(mmr)
                    season -= 1
                except Exception:
                    player.mmr_history.reverse()
                    break

            player.kd = player.kills / player.deaths
            player.headshot_ratio = player.headshots / player.kills
            player.winloss = player.wins / player.losses
            player.kills_per_game = player.kills / (player.wins + player.losses)

        await auth.close()

    asyncio.get_event_loop().run_until_complete(_download(usernames, email, password))


def plot_ranks():
    def season_number_to_yearseason(number):
        year = number // 4
        season = number % 4 + 1
        return f'Y{year}S{season}'

    global players

    plot = plt.figure()
    ax1 = plot.add_subplot(111)

    for player in players:
        seasons = []
        for season in range(len(player.mmr_history)):
            season_number = 21 + season
            seasons.append(season_number_to_yearseason(season_number))
        ax1.plot(seasons, player.mmr_history, label=player.username, linestyle='-')
    plt.title('MMR by Season')
    plt.xlabel('Season')
    plt.ylabel('MMR')
    plt.legend(loc='lower right')
    plt.show()


def write_players_to_csv(team_name):
    global players

    general_fields = ['Player', 'Kills', 'Deaths', 'K/D', 'Kills/Game', 'Headshots', 'Headshot Ratio', 'Wins', 'Losses', 'Win/Loss', 'Rank', 'Time Played (Hrs)']
    op_fields = ['Player', 'Operator', 'Kills', 'Deaths', 'K/D', 'Headshots', 'Headshot Ratio', 'Wins', 'Losses', 'Win/Loss', 'Win Percentage', 'Time Played (Hrs)']

    general_data = []
    op_data = []
    for player in players:
        data = []
        data.append(player.username)
        data.append(player.kills)
        data.append(player.deaths)
        data.append(player.kd)
        data.append(player.kills_per_game)
        data.append(player.headshots)
        data.append(player.headshot_ratio)
        data.append(player.wins)
        data.append(player.losses)
        data.append(player.winloss)
        data.append(player.rank_name)
        data.append(player.time_played)
        general_data.append(data)

        # Write op data for player
        op_names = list(player.operators.keys())
        op_names.sort()
        for op_name in op_names:
            op = player.operators[op_name]
            kd = 0 if op.deaths == 0 else op.kills / op.deaths
            headshot_ratio = 0 if op.kills == 0 else op.headshots / op.kills
            win_loss = 0 if op.losses == 0 else op.wins / op.losses
            win_perc = 0 if (op.wins + op.losses) == 0 else op.wins / (op.wins + op.losses)
            row = [player.username, op_name, op.kills, op.deaths, kd, op.headshots, headshot_ratio, op.wins, op.losses, win_loss, win_perc, op.time_played / 3600]
            op_data.append(row)

    with open(f'data/{team_name}-player_general_data.csv', 'w') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(general_fields)
        csvwriter.writerows(general_data)

    with open(f'data/{team_name}-operator_data.csv', 'w') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(op_fields)
        csvwriter.writerows(op_data)


if __name__ == '__main__':
    try:
        mkdir('data')
    except FileExistsError:
        pass
    with open('auth.json', 'r') as f:
        auth = json.load(f)

    # uplay_ids = ['CodingPenguin1', 'IchorousEagle', 'ShadewMane', 'SharkMAH', 'King.Zeus946', 'Sp00oon', 'AuerryAce', 'SovietSombrero']
    uplay_ids = ['Danio.FPU', 'Royguin.FPU', 'gokurocks10.FPU', 'LoneSniper.FPU', 'ProSoup.FPU', 'Tuckin.FPU', 'draza.FPU', 'Ambrose891.FPU', 'Dr__Popper.FPU']
    get_stats(uplay_ids, auth['email'], auth['password'])
    # plot_ranks()
    write_players_to_csv('FPU')
