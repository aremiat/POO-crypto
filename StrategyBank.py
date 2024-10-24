import numpy as np
import pandas as pd
from Classes.Strategy import Strategy, RankedStrategy, OptimizationStrategy

class MinVarianceStrategy(OptimizationStrategy):
    def objective_function(self, weights, expected_returns, cov_matrix):
        # Fonction objectif : variance du portefeuille
        portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
        return portfolio_variance
    
class MaxSharpeStrategy(OptimizationStrategy):
    def objective_function(self, weights, expected_returns, cov_matrix):
        portfolio_return = np.dot(weights, expected_returns) * 252  # Annualisé
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)) * 252)
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility
        # Nous voulons maximiser le ratio de Sharpe, donc nous minimisons son opposé
        return -sharpe_ratio
    
class EqualRiskContributionStrategy(OptimizationStrategy):
    def objective_function(self, weights, expected_returns, cov_matrix):
        # Calcul de la contribution au risque de chaque actif
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        marginal_risk_contribution = np.dot(cov_matrix, weights) / portfolio_volatility
        risk_contributions = weights * marginal_risk_contribution

        # Calcul de l'objectif ERC
        target_risk = portfolio_volatility / len(weights)
        return np.sum((risk_contributions - target_risk) ** 2)
    
class EqualRiskContributionStrategy(OptimizationStrategy):
    def __init__(self, lmd_mu=0.25, lmd_var=0.1, **kwargs):
        super().__init__(**kwargs)
        self.lmd_mu = lmd_mu
        self.lmd_var = lmd_var

    def objective_function(self, weights, expected_returns, cov_matrix):
        N = len(weights)
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        marginal_risk_contribution = np.dot(cov_matrix, weights) / portfolio_volatility
        risk_contributions = weights * marginal_risk_contribution

        # Calcul de l'objectif ERC avec les paramètres lmd_mu et lmd_var
        risk_objective = np.sum((risk_contributions - portfolio_volatility / N) ** 2)
        return_value_objective = -self.lmd_mu * np.dot(weights, expected_returns)
        variance_objective = self.lmd_var * portfolio_volatility ** 2
        return risk_objective + return_value_objective + variance_objective
    
class EqualWeightStrategy(Strategy):
    def get_position(self, historical_data, current_position):
        num_assets = historical_data.shape[1]
        weights = pd.Series(1 / num_assets, index=historical_data.columns)
        return weights
    
class RandomStrategy(Strategy):
    def get_position(self, historical_data, current_position):
        weights = np.random.rand(len(historical_data.columns))
        weights /= weights.sum()
        return pd.Series(weights, index=historical_data.columns)

class ValueStrategy:
    def __init__(self, historical_data, lookback_period=365, alpha = 1):
        self.lookback_period = lookback_period
        self.historical_data = pd.read_csv(historical_data)
        self.historical_data['Date']  = pd.to_datetime(self.historical_data['Date'])
        self.historical_data.set_index('Date', inplace=True)
        self.alpha = alpha
    
    def rank_assets(self):
        """
        on classe les actifs puis on leur ajoute un parametre alpha
        qui determine le coefficient de risque du portefeuille
        On short les actifs qui ont le plus performé car phénoméne de mean reversion
        """
        last_prices = self.historical_data.iloc[-1]  # Dernier prix de chaque actif
        prices_one_year_ago = self.historical_data.iloc[-self.lookback_period]  # Prix d'il y a un an

        # Calcul du coefficient
        coef_asset = last_prices / prices_one_year_ago

        # On peut éventuellement normaliser ou utiliser ce coefficient dans d'autres calculs
        coef_asset = coef_asset.fillna(0)  # Remplacer les NaN par 0 si nécessaire

        # Afficher ou retourner le coefficient

        # latest_returns = total_returns.iloc[-1]
        ranked_assets = coef_asset.rank(ascending=False, method='first').sort_values()
        
        num_assets = ranked_assets.count()
        sum_of_ranks = ranked_assets.sum()
        average = sum_of_ranks / num_assets
        weights = (ranked_assets - average) * self.alpha
        
        total_abs_ranks = sum(abs(weights))

        normalized_weights = weights / total_abs_ranks
               
        return normalized_weights

class MomentumStrategy:
    
    def __init__(self, historical_data, lookback_period=365):
        self.lookback_period = lookback_period
        self.historical_data = pd.read_csv(historical_data)
        self.historical_data['Date']  = pd.to_datetime(self.historical_data['Date'])
        self.historical_data.set_index('Date', inplace=True)
    
    def rank_assets(self):
        """
        On alloue plus de poids au actifs qui ont surperformé
        """
        returns = self.historical_data.pct_change().dropna()
        total_returns = returns.rolling(window=self.lookback_period - 30).apply(lambda x: (1 + x).prod() - 1)
        latest_returns = total_returns.iloc[-1]
        ranked_assets = latest_returns.rank(ascending=False, method='first').sort_values()
        print(ranked_assets)
        # Nombre total d'actifs
        num_assets = ranked_assets.count()

        # Déterminer la moitié supérieure et inférieure
        split_index = num_assets // 2  # Indice pour séparer les longs et shorts
        # Sélectionner les actifs longs et shorts
        long_assets = ranked_assets.index[:split_index]  # Actifs de la moitié supérieure pour long
        short_assets = ranked_assets.index[split_index:]  # Actifs de la moitié inférieure pour short
        
        # Initialiser les poids
        weights = pd.Series(0, index=latest_returns.index)
        
        # Affecter des poids longs (positifs) à la moitié supérieure
        weights[long_assets] = (1 / split_index) / 2  # Distribution égale des poids longs

        # Affecter des poids shorts (négatifs) à la moitié inférieure
        weights[short_assets] = (-1 / split_index) / 2 # Distribution égale des poids shorts
        
        return weights

class MinVolStrategy:
    
    def __init__(self, historical_data):
        self.historical_data = pd.read_csv(historical_data)
        self.historical_data['Date']  = pd.to_datetime(self.historical_data['Date'])
        self.historical_data.set_index('Date', inplace=True)
        
    def rank_assets(self):
        
        returns = self.historical_data.pct_change().dropna()
        # Calculer la variation quotidienne de la performance pour les actifs sélectionnés
        daily_variation = returns.diff()
        print(daily_variation)
        
        # Calculer les poids relatifs en divisant la variation quotidienne de chaque actif par la variation totale
        relative_weights = daily_variation.div(daily_variation.sum(axis=1), axis=0)
        relative_weights = relative_weights.iloc[-1]
        # Remplacer les NaN par des zéros
        self.adjusted_weights_over_time = relative_weights.fillna(0)
        
        return relative_weights
    
    

data = pd.read_csv(r"C:\Users\admin\Desktop\cours dauphine\poo\projet\data\database.csv")
data['Date']  = pd.to_datetime(data['Date'])
data.set_index('Date', inplace=True)

data = data.pct_change().dropna()
total_returns = data.rolling(window=365).apply(lambda x: (1 + x).prod() - 1)
 
a = MomentumStrategy(r"C:\Users\admin\Desktop\cours dauphine\poo\projet\data\database.csv")
a.rank_assets()

a = ValueStrategy(r"C:\Users\admin\Desktop\cours dauphine\poo\projet\data\database.csv")

a.rank_assets()

a = MinVolStrategy(r"C:\Users\admin\Desktop\cours dauphine\poo\projet\data\database.csv")

a.rank_assets()