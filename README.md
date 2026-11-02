# Website Funnel Drop-off Analyzer

An end-to-end e-commerce analytics project using Python, Jupyter, and Streamlit. It analyzes how sessions progress through a product interaction funnel and provides an interactive dashboard with date, funnel-step, brand, and category filters.

## Project overview

The project uses event-level data from the [eCommerce Events History in Cosmetics Shop](https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop). Each row represents a recorded event. The source includes product views, cart additions, cart removals, and purchases, along with session, brand, and category fields. The dataset covers October 2019 through February 2020; this project analyzes **October 2019** to keep the first version manageable on a personal computer.

### Questions explored

- How many sessions progress from product view to cart to purchase?
- At which transition is the largest session drop-off?
- How do daily conversion rates vary over October?
- Do brand or category segments show different funnel patterns?
- Which days have unusually high drop-off and may merit further investigation?

## Repository structure

```text
website-funnel-dropoff-analyzer/
├── README.md
├── .gitignore
├── website_funnel_dropoff_analyzer.ipynb
└── streamlit_app/
    ├── app.py
    ├── requirements.txt
    └── data/
        └── 2019-Oct.csv   # local only; do not commit the dataset
```

Use your **latest completed notebook** as `website_funnel_dropoff_analyzer.ipynb`. In its setup cell, set the data path to:

```python
DATA_PATH = Path("streamlit_app/data/2019-Oct.csv")
```

## Run the Jupyter analysis

1. Download `2019-Oct.csv` from the [Kaggle dataset](https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop).
2. Place it in `streamlit_app/data/2019-Oct.csv`.
3. Open `website_funnel_dropoff_analyzer.ipynb` in Jupyter and run the cells from top to bottom.

The notebook cleans event timestamps and session IDs, calculates an ordered session funnel, explores daily conversion, checks a statistical high-drop-off flag, and compares the first eight days of October with the rest of the month.

## Run the Streamlit dashboard

From the repository root, create and activate a virtual environment, install dependencies, and launch the app:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r streamlit_app/requirements.txt
python -m streamlit run streamlit_app/app.py
```

The app opens in a browser. Its sidebar includes:

- A date range based on the session's first qualifying view (UTC)
- A conversion step to inspect: view-to-cart, cart-to-purchase, or view-to-purchase
- A segment selector for all sessions, a brand, or a category

The dashboard shows a dataset summary, session counts and rates, an ordered funnel chart, daily conversion and drop-off flags, and raw event volume by calendar date. Streamlit caches loaded and transformed data to avoid repeating work during interactions.

## Funnel definition

The session funnel is **view → cart → purchase**:

1. A session reaches **view** when a product-view event occurs.
2. It reaches **cart** when a cart event occurs after a view in that session.
3. It reaches **purchase** when a purchase event occurs after that qualifying cart event.

The analysis counts sessions, not event rows. A session can contain repeated events. `remove_from_cart` does not reset funnel progress, and a purchase is not matched to a specific product previously added to cart. In the brand/category dashboard, the sequence is calculated using events from the selected segment; sessions can therefore qualify separately for different segments.

## October 2019 results

The completed October analysis found:

| Stage | Sessions | Conversion from prior stage |
|---|---:|---:|
| Product view | 826,147 | — |
| Cart after view | 178,396 | 21.6% |
| Purchase after cart | 19,414 | 10.9% |

Overall view-to-purchase conversion was **2.3%**.

The first eight days differed from the remainder of the month:

| First-view period | View-to-cart | Cart-to-purchase | View-to-purchase |
|---|---:|---:|---:|
| Oct 1–8 | 34.3% | 6.5% | 2.2% |
| Oct 9–31 | 16.3% | 14.7% | 2.4% |

The IQR screening rule marked unusually high cart-to-purchase drop-off on October 1, 2, 6, 7, and 8. These are review cues, not explanations of why behavior differed.

## Data limitations

- This is observational data from one cosmetics e-commerce store during one historical month.
- The event log does not contain device, campaign, landing-page, or checkout events, so those dimensions are not analyzed.
- Brand and category are product attributes. They do not replace traffic-source or device segmentation.
- The funnel does not establish why users stop progressing and does not imply a causal relationship.
- Daily funnel metrics assign sessions to their first qualifying view date. The raw event-volume chart instead uses each event's calendar date.
- The IQR rule is a lightweight statistical screening method, not a trained machine-learning model.

## Dataset attribution

Dataset: [eCommerce Events History in Cosmetics Shop](https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop), collected by the Open CDP project. The dataset page requests attribution to the dataset and REES46 Marketing Platform when using the data.
