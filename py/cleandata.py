import os.path

import pandas as pd


def get_data(file_path):
    location_data = pd.read_csv(
        os.path.dirname(__file__) + "/../data/shrid_loc_names.csv"
    )
    location_data = location_data.astype("string")
    location_data = location_data[location_data["state_name"] == "goa"]

    districts = location_data[["shrid2", "district_name"]]
    districts.loc[:, "shrid2"] = districts["shrid2"].str.split("-").str.get(2)
    districts = districts.drop_duplicates()

    subdistricts = location_data[["shrid2", "subdistrict_name"]]
    subdistricts.loc[:, "shrid2"] = subdistricts["shrid2"].str.split("-").str.get(3)
    subdistricts = subdistricts.drop_duplicates()

    df = pd.read_csv(file_path, parse_dates=["year"], date_format="%Y")

    df[["pc11_state", "pc11_distr", "pc11_subdi"]] = df[
        ["pc11_state", "pc11_distr", "pc11_subdi"]
    ].astype("string")
    df["pc11_subdi"] = "0" + df["pc11_subdi"]

    df = df.merge(districts, how="left", left_on="pc11_distr", right_on="shrid2")
    df = df.drop(["shrid2"], axis=1)

    df = df.merge(subdistricts, how="left", left_on="pc11_subdi", right_on="shrid2")
    df = df.drop(["shrid2"], axis=1)

    df["pc11_state"] = "Goa"

    df = df.rename(
        columns={
            "year": "Year",
            "town_villa": "Town_or_village",
            "district_name": "District",
            "subdistrict_name": "Subdistrict",
        }
    )

    df["District"] = df["District"].str.title()
    df["Subdistrict"] = df["Subdistrict"].str.title()

    df = df.drop(["fid", "pc11_state", "pc11_distr", "pc11_subdi"], axis=1)
    df = df.dropna(axis=1, how="all")
    df = df.set_index(
        ["District", "Subdistrict", "Town_or_village", "Year"]
    ).sort_index()

    return df
