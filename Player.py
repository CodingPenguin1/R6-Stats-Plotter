class Player:
    def __init__(self, username, operators):
        self.username = username
        self.operators = operators

        self.wins = 0
        self.losses = 0
        self.kills = 0
        self.deaths = 0
        self.headshots = 0

        self.mmr_history = []
        self.rank_name = ''
        self._generate_overall_stats()

    def _generate_overall_stats(self):
        for operator_name in self.operators.keys():
            operator = self.operators[operator_name]
            self.wins += operator.wins
            self.losses += operator.losses
            self.kills += operator.kills
            self.deaths += operator.deaths
            self.headshots += operator.headshots

    def stats(self):
        return {'wins': self.wins, 'losses': self.losses, 'kills': self.kills, 'deaths': self.deaths, 'headshots': self.headshots}

    def __str__(self):
        return f'{self.username} ({self.rank_name})'
