#!/usr/bin/env python
# coding: utf-8

import garminconnect as gc
import datetime
import json
import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import requests
import logging


logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def init_api(email, password):
    """Initialize Garmin API with your credentials."""

    try:

        api = gc.Garmin(email, password)
        api.login()

        # Save session dictionary to json file for future use
        with open("session.json", "w", encoding="utf-8") as f:
            json.dump(api.session_data, f, ensure_ascii=False, indent=4)
    except (
        gc.GarminConnectConnectionError,
        gc.GarminConnectAuthenticationError,
        gc.GarminConnectTooManyRequestsError,
        requests.exceptions.HTTPError,
    ) as err:
        logger.error("Error occurred during Garmin Connect communication: %s", err)
        st.error(err)
        return None

    return api
    
st.title("A stride-vs-speed webapp")
st.header(":runner: Analyze how your stride length changes with your pace :runner:")

st.write("First, login in the sidebar to the left.")

if 'submit' not in st.session_state:
    st.session_state['submit']=False

with st.sidebar:
    with st.form(key='login'):
        st.markdown("**Garmin Connect**")
        user=st.text_input("Username",key='user')
        pwd=st.text_input("Password",type="password", key='pwd')
        st.session_state.submit=st.form_submit_button(label="Login")

st.text(st.session_state)

#def set_submit():
#    st.session_state.submit = True

if st.session_state['FormSubmitter:login-Login']:
    if "api" not in st.session_state:
        st.session_state['api'] = init_api(st.session_state.user,st.session_state.pwd)
    if st.session_state.api is not None:
        api = st.session_state.api
        st.sidebar.markdown("Logged in!")
        with st.form(key='dates'):
            start_date, end_date=st.date_input('Time interval to consider',[datetime.date(2022,9,1),datetime.date.today()],max_value=datetime.date.today())
            activities = api.get_activities_by_date(
                    start_date, end_date, "running"
                    )
            dates=st.form_submit_button(label='Search activities')
        if dates:
            st.text("Found {} running activities".format(len(activities)))
            data=[]
            if len(activities) > 1:
                for activity in activities:
                    activity_id = activity["activityId"]
                    # display_text(activity)
                    # print("\n")
                    laps=api.get_activity_splits(activity_id)['lapDTOs']
                    data.extend([
                        {"activity_type" : activity['activityType']['typeKey'],
                        "activity_start": activity['startTimeGMT'],
                        "activity_distance": activity['distance'],
                        "lap_start": l['startTimeGMT'], 
                        "lap_distance": l['distance'],
                        "lap_duration": l['duration'],
                        "elev_gain": l['elevationGain'],
                        "elev_loss": l['elevationLoss'],
                        "speed": l['averageSpeed'],
                        "stride_length": l['strideLength']/100} for l in laps])

                lap_df=pd.DataFrame(data)#,dtype={'activity_start':'datetime64[ns]','lap_start':'datetime64[ns]'})

                lap_df=lap_df.astype({'activity_start':'datetime64[ns]','lap_start':'datetime64[ns]'})
                #lap_df.dtypes
                lap_df['activity_start']=lap_df.activity_start.dt.tz_localize('GMT')
                lap_df['lap_start']=lap_df.lap_start.dt.tz_localize('GMT')


                lap_df['pace']=lap_df.apply(lambda x: '{}\'{:.0f}"'.format(math.floor((x.lap_duration/x.lap_distance*1000)//60),(x.lap_duration/x.lap_distance*1000)%60), axis=1)



                clean_df=(lap_df.query('(activity_type == "track_running" and lap_distance >= 400) or (activity_type == "running" and lap_distance >= 1000)')
                    .query('(elev_gain/lap_distance < 0.06) and (elev_loss/lap_distance < 0.06)'))


                c1, c0 = np.polyfit(clean_df.speed,clean_df.stride_length,1)


                fig = px.scatter(clean_df,
                    x="speed", 
                    y="stride_length", 
                    title="Stride length vs speed",
                    width=800,
                    height=600,
                    labels={'speed':'speed (m/s)','stride_length':'stride length (m)'},
                    hover_data=['activity_start','pace','lap_distance'],
                    size=clean_df['lap_distance'].clip(0,10**3.5),
                    size_max=10,
                    color='activity_type',
                    template='plotly_dark'
                )
                fig.update_layout(title_x=0.5)
                fig.update_xaxes(showgrid=True,gridwidth=1,gridcolor='lavender')
                fig.update_yaxes(showgrid=True,gridwidth=1,gridcolor='lavender')
                #fig.layout.update(xaxis2 = go.layout.XAxis(overlaying='x',side='top'))
                fig.add_shape(
                        type='line',
                        x0=clean_df.speed.min()*0.98,
                        y0=c0+c1*clean_df.speed.min()*0.98,
                        x1=clean_df.speed.max()*1.02,
                        y1=c0+c1*clean_df.speed.max()*1.02,
                        line=dict(
                            dash='dot', color='gray'
                        )
                )
                st.plotly_chart(fig, theme=None)
                "Your coefficient appears to be {:.2f}".format(c1)
            else:
                "Please load at least two activities!"
    #else:
    #    st.error("Logging error")







