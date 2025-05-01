
def googleAnalytics():
    """
    Placeholder function to simulate fetching Google Analytics data.
    """
    return {
        "GoogleAnalytics": {
            "sessions": 5000,
            "bounceRate": 0.45,
            "avgSessionDuration": 150,
            "pageViews": 10000,
            "newUsers": 3000,
            "conversionRate": 0.03,
            "revenue": 15000
        }
    }

def hotjar():
    """
    Placeholder function to simulate fetching Hotjar data.
    """
    return {
        "Hotjar": {
            "heatmapClicks": 1500,
            "scrollDepth": 0.65,
            "sessionRecordings": 500,
            "abTestSuccessRate": 0.5
        }
    }

def facebook():
    """
    Placeholder function to simulate fetching Facebook Ads data.
    """
    return {
        "Facebook": {
            "adSpend": 2000,
            "clickThroughRate": 0.07,
            "conversionRate": 0.05,
            "costPerClick": 1.2,
            "impressions": 100000,
            "leadsGenerated": 500,
            "returnOnAdSpend": 2.5
        }
    }

def segment():
    """
    Placeholder function to simulate fetching Segment data.
    """
    return {
        "Segment": {
            "events": 2000,
            "activeUsers": 3000,
            "avgRevenuePerUser": 5.0,
            "userRetentionRate": 0.8,
            "userChurnRate": 0.1
        }
    }

# Aggregating Data for the LLM Agent

# Main Function to Simulate the LLM Agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage,SystemMessage,AIMessage
from app.core.config import settings
from app.llm.prompts import ANALYZATION_PROMPT
def aggregate_data():
    """
    Aggregates data from all data sources for analysis by the LLM agent.
    """
    ga_data = googleAnalytics()
    hotjar_data = hotjar()
    fb_data = facebook()
    segment_data = segment()

    report_data = {
        "key_metrics": {
            "LTV": segment_data["Segment"]["avgRevenuePerUser"] * 12,
            "CAC": fb_data["Facebook"]["adSpend"] / fb_data["Facebook"]["leadsGenerated"],
            "conversion_rate": ga_data["GoogleAnalytics"]["conversionRate"],
            "facebook_conversion_rate": fb_data["Facebook"]["conversionRate"],
            "ltv_cac_ratio": round((segment_data["Segment"]["avgRevenuePerUser"] * 12) / (fb_data["Facebook"]["adSpend"] / fb_data["Facebook"]["leadsGenerated"]), 2)
        },
        "event_based_tracking": {
            "google_analytics": ga_data["GoogleAnalytics"],
            "hotjar": hotjar_data["Hotjar"]
        },
        "campaign_outcomes": fb_data["Facebook"],
        "user_metrics": segment_data["Segment"]
    }
    return report_data

def generate_report(query="Generate a detailed growth analytics report based on provided data"):
    """
    Generates a detailed growth performance report using LangChain's ChatOpenAI.
    """
    data = aggregate_data()

    # Convert aggregated data into a readable text for AIMessage
    data_message = f"""
    Key Metrics:
    - LTV: {data['key_metrics']['LTV']}
    - CAC: {data['key_metrics']['CAC']}
    - LTV:CAC Ratio: {data['key_metrics']['ltv_cac_ratio']}
    - Conversion Rate (Google Analytics): {data['key_metrics']['conversion_rate']}
    - Facebook Conversion Rate: {data['key_metrics']['facebook_conversion_rate']}

    Event-Based Tracking:
    Google Analytics:
    - Bounce Rate: {data['event_based_tracking']['google_analytics']['bounceRate']}
    - Avg Session Duration: {data['event_based_tracking']['google_analytics']['avgSessionDuration']}
    - New Users: {data['event_based_tracking']['google_analytics']['newUsers']}
    Hotjar:
    - Heatmap Clicks: {data['event_based_tracking']['hotjar']['heatmapClicks']}
    - Scroll Depth: {data['event_based_tracking']['hotjar']['scrollDepth']}
    - A/B Test Success Rate: {data['event_based_tracking']['hotjar']['abTestSuccessRate']}

    Campaign Outcomes:
    - Facebook Ad Spend: {data['campaign_outcomes']['adSpend']}
    - Leads Generated: {data['campaign_outcomes']['leadsGenerated']}
    - ROAS: {data['campaign_outcomes']['returnOnAdSpend']}
    - Click Through Rate: {data['campaign_outcomes']['clickThroughRate']}

    User Metrics:
    - Active Users: {data['user_metrics']['activeUsers']}
    - User Retention Rate: {data['user_metrics']['userRetentionRate']}
    - User Churn Rate: {data['user_metrics']['userChurnRate']}
    """

    messages = [
        SystemMessage(content=ANALYZATION_PROMPT),
        HumanMessage(content=query),
        AIMessage(content=data_message),
    ]

    # Langchain ChatOpenAI invocation
    llm = ChatOpenAI(model=settings.LLM_MODEL_NAME, temperature=0.2)
    report = llm.invoke(messages)

    return report.content

# Simulate the report generation
generated_report = generate_report()
print(generated_report)