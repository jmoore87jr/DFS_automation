"""Generate fake players and prize structure, figure out how to optimize x lineups
and run n trials. Store % of lineups each player is in. Calculate $/lineup for each 
player. WRITE A PLAN FOR HOW TO DO THIS BEFORE STARTING"""

# Plan:
  # seems like the good lineups are winning too much...I think I either don't use int() for scores or I increase player variance
  # this could be a good time to use classes
  # i'm not using positions - this will make optimization faster and it doesn't matter for toy game purposes
  # use random with list comp to generate dict of {player: [salary, expected_points, actual_points]}
    # can also use random to make sure I have some players with expected pts/$ 6 and some with 4
    # add ownership % to dict.values after simulating lineups
    # can I correlate players somehow?
  # write function to optimize
    # objective: max(expected_points)
    # constraint 1: salary <= 50000
    # constraint 2: players == 8
    # constraint 3: PG >= 1 and PG <= 3
    # constraint 4: SG >= 1 and SG <= 3
    # constraint 5: SF >= 1 and SF <= 3
    # constraint 6: PF >= 1 and PF <= 3
    # constraint 7: C >= 1 and C <= 2
    # constraint 8: ownership - set max and min with ownership projection regression formula


import math
import pulp as pl
import numpy as np
import pandas as pd
from collections import defaultdict

def roundup(x): # round salaries to nearest 100
    return int(math.ceil(x / 100)) * 100

def generate_players(p):
    """Generates dictionary with {player: salary, exp_pts, act_pts}"""
    players = {}
    positions = ['PG', 'SG', 'SF', 'PF', 'C']
    i = 0
    while len(players) < p:
        salary = roundup(np.random.normal(5784, 2211))
        if salary >= 3000: # only take salaries > 3000
            position = np.random.choice(positions)
            exp_pts = np.random.normal(salary*0.005, salary*0.00052)
            stdev = -4.39 + 3.63*math.log(exp_pts)
            act_pts = np.random.normal(exp_pts, stdev)
            exp_ppd = (exp_pts / salary) * 1000
            players["p{}".format(i)] = [position, int(salary), round(exp_pts, 2), round(exp_ppd, 2), int(act_pts)]
            i += 1
    return players

def enter_players():
    # import csv of players
    # return dictionary {player: position, salary, exp_pts, value, act_pts}. calculate act_pts from stdev
    df = pd.read_csv('ownership_projections.csv')
    d = defaultdict()
    stdev = df['pts'] * df['stdev/pts'] / 10
    salary = df['salary']
    value = df['value']
    exp_pts = df['pts']
    names = df['Unnamed: 0']
    for i in range(len(df.index)): 
        name = names[i].replace(' ', '_').replace('-', '_')
        d[name] = ['none', salary[i], exp_pts[i], value[i], np.random.normal(exp_pts[i], stdev[i])]
    return d

def optimize_lineups(p, n, random=True):
    """Use pulp solver to find top n optimal lineups using exp_pts from p randomly generated players. Returns 
    DataFrame of the optimal lineups and their actual scores"""

    if random:
        players = generate_players(p)
    else:
        players = enter_players()

    #for k in players.keys():
        #print(k)
    
    high_score = 0
    lnps = defaultdict()

    for _ in range(n):
        # define problem
        prob = pl.LpProblem('DFS', pl.LpMaximize)

        # set solver
        solver = pl.PULP_CBC_CMD()

        # create decision variables
        player_lineup = [pl.LpVariable(player, cat='Binary') for player in players.keys()]
        """PG = [pl.LpVariable('p{}'.format(i), cat='Binary') for i in range(p)]
        SG = [pl.LpVariable('p{}'.format(i), cat='Binary') for i in range(p)]
        SF = [pl.LpVariable('p{}'.format(i), cat='Binary') for i in range(p)]
        PF = [pl.LpVariable('p{}'.format(i), cat='Binary') for i in range(p)]
        C = [pl.LpVariable('p{}'.format(i), cat='Binary') for i in range(p)]
        for i, pos in enumerate(players.keys()):
            if players[pos][0] == 'PG':
                PG[i] = 1
            elif players[pos][0] == 'SG':
                SG[i] = 1
            elif players[pos][0] == 'SF':
                SF[i] = 1
            elif players[pos][0] == 'PF':
                PF[i] = 1
            elif players[pos][0] == 'C':
                C[i] = 1"""
        # define constraints:
        # sum of the binary player_lineup == 8 players
        prob += (pl.lpSum(player_lineup[i] for i in range(p)) == 8)
        # salary <= 50000
        prob += (pl.lpSum(players['{}'.format(player_lineup[i])][1]*player_lineup[i] for i in range(p)) <= 50000)
        # positions
        """prob += (pl.lpSum(PG[i] for i in range(p)) >= 1)
        prob += (pl.lpSum(PG[i] for i in range(p)) <= 3)
        prob += (pl.lpSum(SG[i] for i in range(p)) >= 1)
        prob += (pl.lpSum(SG[i] for i in range(p)) <= 3)
        prob += (pl.lpSum(SF[i] for i in range(p)) >= 1)
        prob += (pl.lpSum(SF[i] for i in range(p)) <= 3)
        prob += (pl.lpSum(PF[i] for i in range(p)) >= 1)
        prob += (pl.lpSum(PF[i] for i in range(p)) <= 3)
        prob += (pl.lpSum(C[i] for i in range(p)) >= 1)
        prob += (pl.lpSum(C[i] for i in range(p)) <= 2)"""
        # lineup projection less than the previous one
        if high_score:
            prob += (pl.lpSum(players['{}'.format(player_lineup[i])][2]*player_lineup[i] for i in range(p)) <= high_score - .01)

        # define objective function:
        # maximize sum of expected_points * player_lineup (binary)
        prob += pl.lpSum(players['{}'.format(player_lineup[i])][2]*player_lineup[i] for i in range(p))

        # solve
        prob.solve(solver)

        # print results for each lineup
        d = defaultdict()
        print(players)
        print(player_lineup)
        for plyr in player_lineup:
            print(plyr)
            if pl.value(plyr) == 1:
                d[str(plyr)] = players[str(plyr)]
        results = pd.DataFrame.from_dict(d, orient='index', 
                columns=['Position', 'Salary', 'exp_pts', 'exp_ppd', 'act_pts'])
        total_salary = sum(results['Salary'])
        exp_score = sum(results['exp_pts'])
        act_score = sum(results['act_pts']) 
        print(results)
        print("Total Salary: {}".format(total_salary))
        print("Expected score: {}".format(exp_score))
        print("Actual score: {}".format(act_score))

        # set high_score
        high_score = sum(results['exp_pts'])

        # store lineup
        lnps['lineup_{}'.format(_)] = (list(results.index), act_score)

    # print results  
    result = pd.DataFrame.from_dict(lnps, orient='index', columns=['lineup', 'score']).sort_values('score', ascending=False)
    for k in players.keys():
        print("{}: {}".format(k, players[k]))
    print(result)

    return [results, result, players] # need to return more stuff from here in order to re-roll later and alter 'result'





