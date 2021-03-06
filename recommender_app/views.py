import numpy as np

from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render

from config import DATASET_DIR
from recommender.evaluation import ndcg_at_k
from recommender.fairness_reg_als import FairnessRegALS
from recommender.scrapper_amazon import get_data
from recommender.util import dataframe_to_matrix, divide_item_popularity, load_dataset

# prepare dataset
dataset_frame = load_dataset(DATASET_DIR)
R_dataset = dataframe_to_matrix(dataset_frame)
users_list = dataset_frame.user_id.unique()

# divide item popularity
short_head, medium_tail = divide_item_popularity(dataset_frame)

# load recommender
# hardcode location existing model
MODEL_DIR = 'saved_model/amazon_books_f50_e06_i30/reg-9'
als = FairnessRegALS.load_data(MODEL_DIR)


def index(request, user_id):

    # get recommendation
    if als is None:
        return HttpResponse("model recommender not loaded correctly")

    # get random user on each request
    if user_id is None:
        user_selected = np.random.choice(users_list)
    else:
        user_selected = user_id

    try:
        user_idx = als.user_index.get_loc(user_selected)
    except:
        user_selected = int(user_id)
        user_idx = als.user_index.get_loc(user_selected)

    recommend, recommend_index = als.top_n_recommendation(
        user_selected, 10, with_index=True, with_reviewed=False)

    # get previously reviewed
    reviewed_idx = np.where(R_dataset[user_idx] != 0)[0][:10]
    reviewed = [als.item_index[idx] for idx in reviewed_idx]

    # get tag popularity
    recommend_tag = [(i, 'short-head') if i in short_head else (i, 'medium-tail') for i in recommend]
    reviewed_tag = [(i, 'short-head') if i in short_head else (i, 'medium-tail') for i in reviewed]

    # get ndcg
    all_r_user = R_dataset[user_idx]
    rating_value = all_r_user[recommend_index]
    ndcg = ndcg_at_k(rating_value, 10)

    context = {
        'user_id': user_selected,
        'recommend': recommend,
        'reviewed': reviewed,
        'recommend_tag': recommend_tag,
        'reviewed_tag': reviewed_tag,
        'ndcg': ndcg,
        'rating': rating_value,
    }
    return render(request, 'index.html', context)


def performance(request):
    return render(request, 'performance.html')


def tech_stack(request):
    return render(request, 'tech_stack.html')


def amazon_detail(request, asin):
    context = get_data(asin)
    if context is None:
        raise Http404("ASIN doesn't exist")
    return JsonResponse(context)
