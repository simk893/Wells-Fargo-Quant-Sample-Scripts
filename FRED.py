from datetime import datetime
import json
import time
import matplotlib
import pandas
import requests
from tqdm import tqdm

def get_series(frequency):
    API_KEY = 'b4faab7a30a17140d246cce49bbf42ac'
    BASE_URL = 'https://api.stlouisfed.org/fred/series/search'
    offset, limit = 0 , 1000
    parameters = {'api_key': API_KEY, 'file_type': "json",
                  'search_text': "USA", 'tag_names': "nsa", 'exclude_tag_names': "discontinued",
                  'filter_variable': "frequency", 'filter_value': frequency,
                  'order_by': "observation_start", 'sort_order': 'asc',
                  'offset': offset, 'limit': limit}
    series_dict = {}
    try:
        response = requests.get(BASE_URL, params = parameters)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return series_dict
    except json.JSONDecodeError:
        print("Failed to decode JSON response")
        return series_dict
    total_items = data.get('count', 0)
    with tqdm(total = total_items, desc = "Fetching Data", unit = "Series") as pbar:
        while True:
            for series in data['seriess']:
                series_dict[series['id']] = {'title': series['title'], 
                                             'description': series['notes'],
                                             'units': series['units'],
                                             'popularity': series['popularity'],
                                             'observation_start': series['observation_start'], 
                                             'last_updated': series['last_updated']}
            if len(data['seriess']) < limit:
                pbar.update(len(data['seriess']))
                break
            else:
                parameters['offset'] += limit
                pbar.update(limit)
    return series_dict

def create_series_json(file_name, series_dict):
    dictionary = dict(sorted(series_dict.items()))
    file_path = f'./{file_name}.json'
    with open(file_path, 'w') as json_file:
        json.dump(dictionary, json_file, indent = 2)
    print(f"JSON data written to {file_path}")

def get_series_data(series_id):
    API_KEY = 'b4faab7a30a17140d246cce49bbf42ac'
    BASE_URL = 'https://api.stlouisfed.org/fred/series/observations'
    parameters = {'api_key': API_KEY, 'file_type': 'json',
                  'series_id': series_id, "units": "pc1"}
    response = requests.get(BASE_URL, params = parameters)
    if response.status_code == 200:
        data = response.json() 
        df = pandas.DataFrame(data['observations'])[['date', 'value']]
        df['date'] = pandas.to_datetime(df['date'])
        df['value'] = pandas.to_numeric(df['value'], errors = 'coerce')  
        full_dates = pandas.date_range(start = df['date'].min(), end = df['date'].max(), freq = 'MS')
        df.set_index('date', inplace = True)
        df = df.reindex(full_dates)
        df[series_id] = df['value'].interpolate(method = 'linear').values
        df.drop(columns=['value'], inplace=True)
        return df
    elif response.status_code == 429:
        print(f"Rate limit exceeded. Retrying in {10} seconds...")
        time.sleep(10)
    else:
        print(f"Failed to fetch data for series ID {series_id}. Status code: {response.status_code}")
    return None

def create_series_dataframe(series_data, start_date):
    df = None
    series_ids = series_data.keys()
    with tqdm(total = len(series_ids), desc = "Fetching Data", unit = "Series") as pbar:
        for series_id in series_ids:
            observation_start = data[series_id]['observation_start']
            if observation_start <= start_date:
                data = get_series_data(series_id)
                if data is None:
                    print(f"Failed to fetch data for series ID {series_id}.")
                    pbar.update(1)
                    continue
                if df is None:
                    df = data[data.index >= pandas.to_datetime(start_date)]
                else:
                    data = data[data.index >= pandas.to_datetime(start_date)]
                    df = df.merge(data, left_index = True, right_index = True, how='outer')
            else:
                print(f"Skipping series ID {series_id} due to observation start date {observation_start}.")
            pbar.update(1)
    return df

def plot_cumulative_distribution(data_dict):
    start_dates = [datetime.strptime(info['observation_start'], '%Y-%m-%d') for info in data_dict.values()]
    popularity_scores = [info['popularity'] for info in data_dict.values()]
    
    start_dates_df = pandas.DataFrame({'start_date': start_dates, 'popularity': popularity_scores})
    full_date_range = pandas.date_range(start_dates_df['start_date'].min(), start_dates_df['start_date'].max())
    full_date_df = pandas.DataFrame(full_date_range, columns=['date'])
    
    total_series = len(start_dates_df)
    full_date_df['cumulative_count'] = full_date_df['date'].apply(lambda x: (start_dates_df['start_date'] <= x).sum())
    full_date_df['cumulative_percentage'] = (full_date_df['cumulative_count'] / total_series) * 100
    full_date_df['average_popularity'] = full_date_df['date'].apply(lambda x: start_dates_df[start_dates_df['start_date'] <= x]['popularity'].mean())
    
    max_average_popularity = full_date_df['average_popularity'].max()
    full_date_df['average_popularity_percentage'] = (full_date_df['average_popularity'] / max_average_popularity) * 100
    
    matplotlib.pyplot.figure(figsize=(14, 7))
    matplotlib.pyplot.plot(full_date_df['date'], full_date_df['cumulative_percentage'], label='Cumulative Percentage')
    matplotlib.pyplot.plot(full_date_df['date'], full_date_df['average_popularity_percentage'], label='Average Popularity (%)', color='orange')
    matplotlib.pyplot.xlabel('Date')
    matplotlib.pyplot.ylabel('Cumulative Percentage / Average Popularity (%)')
    matplotlib.pyplot.title('Cumulative Distribution and Average Popularity')
    matplotlib.pyplot.legend()
    matplotlib.pyplot.grid(True)
    matplotlib.pyplot.show()