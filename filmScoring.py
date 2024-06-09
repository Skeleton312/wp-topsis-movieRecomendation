import mysql.connector
import numpy as np

class FilmScoring:
    def __init__(self, db_config, criteria_weights):
        self.db_config = db_config
        self.criteria_weights = criteria_weights
        self.connection = self.connect_db()
        self.alternatives = self.fetch_data()

    def connect_db(self):
        connection = mysql.connector.connect(
            host=self.db_config['host'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            database=self.db_config['database']
        )
        return connection

    def fetch_data(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM films")
        rows = cursor.fetchall()
        alternatives = {row['judul']: row for row in rows}
        cursor.close()
        return alternatives

    def wp(self):
        normalized_data = {}
        
        for key, values in self.alternatives.items():
            weighted_product = 1
            
            for criteria, weight in self.criteria_weights.items():
                if criteria == 'harga':
                    value = values[criteria] ** (-1 * weight)
                else:
                    value = values[criteria] ** weight
                
                weighted_product *= value
            
            normalized_data[key] = weighted_product
        
        total_score = sum(normalized_data.values())
        ranked_alternatives = {key: score / total_score for key, score in normalized_data.items()}
        
        return ranked_alternatives
    
    def topsis(self):
        normalized_data = {}
        
        for film, details in self.alternatives.items():
            weighted_values = np.ones(len(self.criteria_weights))
            
            for i, (criteria, weight) in enumerate(self.criteria_weights.items()):
                if criteria == 'harga':
                    value = 1 / details[criteria]
                else:
                    value = details[criteria]
                
                weighted_values[i] = value ** weight
            
            normalized_values = weighted_values / np.linalg.norm(weighted_values)
            normalized_data[film] = normalized_values
        
        ideal_positive = np.max(list(normalized_data.values()), axis=0)
        ideal_negative = np.min(list(normalized_data.values()), axis=0)
        
        topsis_scores = {}
        
        for film, values in normalized_data.items():
            positive_distance = np.linalg.norm(values - ideal_positive)
            negative_distance = np.linalg.norm(values - ideal_negative)
            
            topsis_score = negative_distance / (positive_distance + negative_distance)
            topsis_scores[film] = topsis_score
        
        return topsis_scores
    
    def mean(self):
        wp_scores = self.wp()
        topsis_scores = self.topsis()
        
        final_scores = {}
        
        for film in wp_scores.keys():
            mean_score = (wp_scores[film] + topsis_scores[film]) / 2
            final_scores[film] = mean_score
        
        return final_scores
    def update_scores_in_db(self):
        cursor = self.connection.cursor()

        # Menghitung final_score
        final_scores = self.mean()

        # Mengupdate nilai score di database
        for film, score in final_scores.items():
            score_float = float(score)
            cursor.execute(
                "UPDATE films SET score = %s WHERE judul = %s",
                (score_float, film))

        self.connection.commit()

        cursor.close()
        return final_scores

# Konfigurasi database
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'movie'
}

# Bobot kriteria
criteria_weights = {'harga': 0.10, 'tahun': 0.20, 'penonton': 0.30, 'rating': 0.30, 'vote': 0.1}
film_scoring=FilmScoring(db_config,criteria_weights)
film_scoring.update_scores_in_db()