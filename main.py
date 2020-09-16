import asyncio
import csv
import json
from os import mkdir

import matplotlib.pyplot as plt
import r6sapi as api

players = []


def get_stats(usernames, email, password):
    async def _download(usernames, email, password):
        global players

        # Pull raw stats
        print('Downloading player statistics')
        auth = api.Auth(email, password)
        api_players = await auth.get_player_batch(usernames, api.Platforms.UPLAY)
        for player in api_players:
            await player.load_all_operators()
            await player.load_gamemodes()
            await player.load_general()
            await player.load_level()
            await player.load_queues()
            await player.load_terrohunt()
            await player.load_weapons()
            players.append(player)

        # Derive stats
        for player in players:
            print(f'Processing player: {player.name}')
            # MMR and rank history
            player.rank_skill = {'mmr': [],
                                 'seasons': [],
                                 'skill_mean': [],
                                 'skill_stdev': []}
            season = -1
            while True:
                try:
                    # print(season)
                    rank = await player.get_rank('cus', season)
                    if season == -1:
                        player.rank_name = rank.rank
                    player.rank_skill['mmr'] = [rank.max_mmr] + player.rank_skill['mmr']
                    player.rank_skill['seasons'] = [rank.season] + player.rank_skill['seasons']
                    player.rank_skill['skill_mean'] = [rank.skill_mean] + player.rank_skill['skill_mean']
                    player.rank_skill['skill_stdev'] = [rank.skill_stdev] + player.rank_skill['skill_stdev']

                    season -= 1
                except Exception as e:
                    break

            # Ranked/Casual stats to dict
            player.ranked_stats = vars(player.ranked)
            player.casual_stats = vars(player.casual)

            # Total wins, losses, winloss, win %
            player.total_wins = player.ranked.won + player.casual.won
            player.total_losses = player.ranked.lost + player.casual.lost
            player.winloss = player.total_wins / player.total_losses
            player.win_percentage = player.total_wins / (player.total_wins + player.total_losses)

            # K/D, KpG and headshot ratio
            player.kd = player.kills / player.deaths
            player.kills_per_game = player.kills / (player.total_wins + player.total_losses)
            player.headshot_ratio = player.headshots / player.kills

            # Accuracy %
            if player.bullets_fired != 0:
                player.accuracy = player.bullets_hit / player.bullets_fired
                if player.accuracy > 1:
                    player.accuracy = 'N/A'
            else:
                player.accuracy = 'N/A'

            # Convert time played to hours
            player.time_played /= 3600

            # Operator stats to dict
            player.operator_stats = {}
            for operator_name in player.operators.keys():
                op = player.operators[operator_name]
                player.operator_stats[operator_name] = vars(op)

            # Weapon stats to dict
            player.weapon_stats = {}
            for weapon in player.weapons:
                player.weapon_stats[weapon.name] = vars(weapon)

        p = players[0]
        attributes = []
        for attr in vars(p):
            if (not attr.startswith('_')) and (not attr.startswith('load_')) and (not attr.startswith('check')) and (not attr.startswith('get')):
                try:
                    attributes.append(attr)
                except Exception:
                    pass
        attributes.sort()

        # for a in attributes:
        #     print(a)
        #     if type(getattr(p, a)) is dict:
        #         keys = list(getattr(p, a))
        #         keys.sort()
        #         for key in keys:
        #             print('  ', key)

        await auth.close()

    asyncio.get_event_loop().run_until_complete(_download(usernames, email, password))


def plot_ranks(team_name, team_members):
    def season_number_to_yearseason(number):
        year = number // 4
        season = number % 4 + 1
        return f'Y{year}S{season}'

    plot = plt.figure()
    ax1 = plot.add_subplot(111)

    print(f'Plotting rank history for team: {team_name}')
    for player in team_members:
        seasons = []
        for season in range(len(player.rank_skill['mmr'])):
            season_number = 21 + season
            seasons.append(season_number_to_yearseason(season_number))
        ax1.plot(seasons, player.rank_skill['mmr'], label=player.name, linestyle='-')
    plt.title('MMR by Season')
    plt.xlabel('Season')
    plt.ylabel('MMR')
    plt.legend(loc='lower right')
    plt.savefig(f'data/{team_name}-ranks.svg'.replace(' ', '_'))


def write_players_to_csv(team_name, team_members):
    general_fields = ['Player', 'Team', 'Kills', 'Deaths', 'K/D', 'Kills/Game', 'Headshots', 'Headshot Ratio', 'Accuracy', 'Wins', 'Losses', 'Win/Loss', 'Rank', 'Time Played (Hrs)']
    op_fields = ['Player', 'Operator', 'Kills', 'Deaths', 'K/D', 'Headshots', 'Headshot Ratio', 'Wins', 'Losses', 'Win/Loss', 'Win Percentage', 'Time Played (Hrs)']

    general_data = []
    op_data = []
    for player in team_members:
        data = []
        data.append(player.name)
        data.append(team_name)
        data.append(player.kills)
        data.append(player.deaths)
        data.append(player.kd)
        data.append(player.kills_per_game)
        data.append(player.headshots)
        data.append(player.headshot_ratio)
        data.append(player.accuracy)
        data.append(player.total_wins)
        data.append(player.total_losses)
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
            row = [player.name, op_name, op.kills, op.deaths, kd, op.headshots, headshot_ratio, op.wins, op.losses, win_loss, win_perc, op.time_played / 3600]
            op_data.append(row)

    print(f'Writing general stats CSV for {team_name}')
    with open(f'data/{team_name}-player_general_data.csv'.replace(' ', '_'), 'w') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(general_fields)
        csvwriter.writerows(general_data)

    print(f'Writing operator CSV for {team_name}')
    with open(f'data/{team_name}-operator_data.csv'.replace(' ', '_'), 'w') as csvfile:
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

    wsu_alpha_uplay = ['CodingPenguin1', 'IchorousEagle', 'ShadewMane', 'SharkMAH', 'King.Zeus946', 'Sp00oon', 'AuerryAce', 'SovietSombrero']
    get_stats(wsu_alpha_uplay, auth['email'], auth['password'])
    wsu_alpha = players.copy()
    players = []
    write_players_to_csv('WSU Alpha', wsu_alpha)
    plot_ranks('WSU Alpha', wsu_alpha)

    fpu_uplay = ['Danio.FPU', 'Royguin.FPU', 'gokurocks10.FPU', 'LoneSniper.FPU', 'ProSoup.FPU', 'Tuckin.FPU', 'draza.FPU', 'Ambrose891.FPU', 'Dr__Popper.FPU']
    get_stats(fpu_uplay, auth['email'], auth['password'])
    fpu = players.copy()
    write_players_to_csv('FPU', fpu)
    plot_ranks('FPU', fpu)

    combined = wsu_alpha + fpu
    write_players_to_csv('WSU and FPU', combined)
    plot_ranks('WSU and FPU', combined)


# Player attributes
# accuracy
# auth
# barricades_deployed
# blind_kills
# bullets_fired
# bullets_hit
# casual
# casual_stats
#    deaths
#    kills
#    lost
#    name
#    played
#    time_played
#    won
# dbno_assists
# dbnos
# deaths
# distance_travelled
# gadgets_destroyed
# gamemodes
#    plantbomb
#    rescuehostage
#    securearea
# headshot_ratio
# headshots
# icon_url
# id
# id_on_platform
# kd
# kill_assists
# kills
# kills_per_game
# level
# matches_lost
# matches_played
# matches_won
# melee_kills
# name
# operator_stats
# operators
# penetration_kills
# platform
# platform_url
# rank_name
# rank_skill
#    mmr
#    seasons
#    skill_mean
#    skill_stdev
# ranked
# ranked_stats
#    deaths
#    kills
#    lost
#    name
#    played
#    time_played
#    won
# ranks
#    cus:-1
#    cus:-2
# rappel_breaches
# reinforcements_deployed
# revives
# revives_denied
# suicides
# terrorist_hunt
# time_played
# total_losses
# total_wins
# total_xp
# url
# url_builder
# userid
# weapon_stats
#    Assault Rifle
#    Handgun
#    Light Machine Gun
#    Machine Pistol
#    Marksman Rifle
#    Shotgun
#    Submachine Gun
# weapons
# win_percentage
# winloss
# xp