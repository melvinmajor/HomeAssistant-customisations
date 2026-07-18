import appdaemon.plugins.hass.hassapi as hass
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import os
import pytz


ICON_MAP = {
    "sunny": "wi-day-sunny.png",
    "clear-night": "wi-night-clear.png",
    "partlycloudy": "wi-day-cloudy.png",
    "cloudy": "wi-cloudy.png",
    "fog": "wi-fog.png",
    "rainy": "wi-rain.png",
    "pouring": "wi-storm-showers.png",
    "lightning": "wi-lightning.png",
    "lightning-rainy": "wi-thunderstorm.png",
    "snowy": "wi-snow.png",
    "snowy-rainy": "wi-sleet.png",
    "hail": "wi-hail.png",
    "windy": "wi-windy.png",
    "windy-variant": "wi-strong-wind.png",
    "exceptional": "wi-hurricane-warning.png",
    "na": "wi-na.png"
}

# Layout constants
IMAGE_WIDTH = 758 # 758 on Kindle EY21
IMAGE_HEIGHT = 880 # Should be 1024 on Kindle EY21 but browser bar has to be kept in mind
MARGIN_X = 45
MARGIN_Y = 35
LEFT_X = MARGIN_X # left side of 2 column
RIGHT_X = 450 # right side of 2 column, smaller than left side
LINE_WIDTH_HEADER = 2
LINE_WIDTH = 1
LINE_FILL_HEADER = 80
LINE_FILL = 120
LINE_FILL_LIGHT = 180
SECTION_SPACING = 25
ICON_SIZE = 94
ICON_SMALL = 64

font_header = ImageFont.truetype("/share/fonts/NotoSans-Bold.ttf", 28)
font_text = ImageFont.truetype("/share/fonts/NotoSans-Regular.ttf", 20)
font_text_small = ImageFont.truetype("/share/fonts/NotoSans-Regular.ttf", 16)
font_emoji = ImageFont.truetype("/share/fonts/Twemoji.Mozilla.ttf", 20)

def uv_category(uv):
    try:
        uv = float(uv)
    except:
        return "Unknown"

    if uv < 3:
        return "Low"
    elif uv < 6:
        return "Medium"
    elif uv < 8:
        return "High"
    elif uv < 11:
        return "Very High"
    else:
        return "Extreme"


class KindleDisplay(hass.Hass):

    def initialize(self):
        #self.log(f"CONFIG DIR LISTING: {os.listdir('/config') if os.path.exists('/config') else 'NO /config'}", level="INFO")

        # First run after 30 seconds
        self.run_in(self.update_display, 30)

        #self.run_every(self.update_display, "now+60", self.args["update_interval"] * 60)
        # Then every hour
        now = datetime.now()
        next_full = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        #next_half = now.replace(minute=30, second=0, microsecond=0)
        #if now.minute >= 30:
        #    next_half += timedelta(hours=1)

        self.run_hourly(self.update_display, next_full)
        #self.run_hourly(self.update_display, next_half)


    def update_display(self, kwargs):
        tz = pytz.timezone("Europe/Brussels")
        now = datetime.now(tz)
        hour = now.hour

        # --- WEATHER ---
        weather_state = self.get_state("weather.irm")
        weather_temp = self.get_state("weather.irm", attribute="temperature")
        # weather_humidity = self.get_state("weather.irm", attribute="humidity")
        weather_uv = self.get_state("weather.irm", attribute="uv_index")


        # --- FORECAST ---
        #forecast = self.get_state("weather.openweathermap_forecast", attribute="forecast")
        raw = self.call_service("weather/get_forecasts", entity_id="weather.open_meteo", type="hourly")
        #self.log(f"Forecast service result: {raw}", level="WARNING") # Debug
        response = raw["result"]["response"]
        entity_key = list(response.keys())[0]
        forecast_list = response[entity_key]["forecast"]

        if not forecast_list:
            self.log("No forecast data available yet, retrying in 60s.", level="WARNING")
            self.run_in(self.update_display, 60)
            return

        hourly_forecasts = forecast_list[:3]
        tomorrow_forecast = forecast_list[24] if len(forecast_list) > 24 else None

        # --- ROOM TEMPERATURES ---
        temp_living = self.get_state("sensor.healthy_home_coach_temperature_sensor")
        humidity_living = self.get_state("sensor.healthy_home_coach_humidity_sensor")
        temp_entrance = self.get_state("sensor.radiator_thermostat_w600_temperature")
        temp_bedroom = self.get_state("sensor.radiator_thermostat_w600_temperature_4")
        temp_bathroom = self.get_state("sensor.radiator_thermostat_w600_temperature_3")
        temp_office = self.get_state("sensor.radiator_thermostat_w600_temperature_2")

        # --- AIR QUALITY ---
        aqi_pm25 = self.get_state("sensor.healthy_home_coach_air_quality")
        aqi_co2 = self.get_state("sensor.healthy_home_coach_carbon_dioxide_sensor")

        # --- IMAGE SETUP ---
        img = Image.new("L", (IMAGE_WIDTH, IMAGE_HEIGHT), 255)
        draw = ImageDraw.Draw(img)


        # --- HEADER ---
        title = "Home Status"
        refresh = f"Last refresh: {now.strftime('%Y-%m-%d %H:%M')}"

        # Measure both texts
        bbox_title = draw.textbbox((0, 0), title, font=font_header)
        title_w = bbox_title[2] - bbox_title[0]
        title_h = bbox_title[3] - bbox_title[1]

        bbox_refresh = draw.textbbox((0, 0), refresh, font=font_text_small)
        refresh_w = bbox_refresh[2] - bbox_refresh[0]
        refresh_h = bbox_refresh[3] - bbox_refresh[1]
        max_h = max(title_h, refresh_h) # Find the tallest text (for baseline alignment)
        y_line = MARGIN_Y + max_h + 15

        # Compute Y offsets so both texts align on the bottom
        title_y = MARGIN_Y + (max_h - title_h)
        refresh_y = MARGIN_Y + (max_h - refresh_h)

        draw.text((MARGIN_X, title_y), title, font=font_header, fill=0)
        draw.text((758 - MARGIN_X - refresh_w, refresh_y), refresh, font=font_text_small, fill=0)
        center = 758 // 2
        draw.line((MARGIN_X, y_line, center - 150, y_line), fill=LINE_FILL_HEADER, width=LINE_WIDTH_HEADER) # Left segment
        draw.line((center + 105, y_line, 758 - MARGIN_X, y_line), fill=LINE_FILL_HEADER, width=LINE_WIDTH_HEADER) # Right segment


        # --- WEATHER TODAY ---
        y = MARGIN_Y + 60
        title = "Current Weather"
        draw.text((MARGIN_X, y), title, font=font_text, fill=0)
        bbox = draw.textbbox((MARGIN_X, y), title, font=font_text)
        text_bottom = bbox[3]
        draw.line((MARGIN_X, text_bottom + 5, 758 - MARGIN_X, text_bottom + 5), fill=LINE_FILL, width=LINE_WIDTH)

        y += 35
        draw.text((MARGIN_X, y), f"{weather_temp}°C – {weather_state}", font=font_text, fill=0)
        #draw.text((MARGIN_X, y + 30), f"Humidity: {weather_humidity}%", font=font_text, fill=0)
        weather_uv = self.get_state("weather.irm", attribute="uv_index")
        uv_cat = uv_category(weather_uv)
        draw.text((MARGIN_X, y + 30), f"UV: {uv_cat} ({weather_uv})", font=font_text_small, fill=0)

        # Icon today
        icon_today = ICON_MAP.get(weather_state, "wi-na.png")
        icon_path = f"/share/kindle/icons/{icon_today}"
        if os.path.exists(icon_path):
            try:
                icon = Image.open(icon_path).convert("RGBA").resize((ICON_SIZE, ICON_SIZE))
                img.paste(icon, (758 - ICON_SIZE - MARGIN_X, y - 5), icon)
            except Exception as e:
                self.log(f"Icon error: {e}", level="WARNING")


        # --- NEXT HOURS (horizontal icons + time + temp) ---
        y += 80
        title = "Next Hours"
        draw.text((MARGIN_X, y), title, font=font_text, fill=0)
        bbox = draw.textbbox((MARGIN_X, y), title, font=font_text)
        text_bottom = bbox[3]
        draw.line((MARGIN_X, text_bottom + 5, 758 - MARGIN_X, text_bottom + 5), fill=LINE_FILL, width=LINE_WIDTH)

        y += 40

        # --- FILTER ONLY FUTURE HOURS ---
        # Round "now" down to the hour
        now_hour = now.replace(minute=0, second=0, microsecond=0)
        future_forecasts = []
        for f in hourly_forecasts:
            raw = f["datetime"]
            # Ensure timezone exists
            if "+" not in raw and "Z" not in raw:
                raw = raw + "+00:00"
            dt = datetime.fromisoformat(raw).astimezone(tz)
            # Skip previous hour AND current hour
            if dt <= now_hour:
                continue
            future_forecasts.append(f)

        # Compute column width for 3 items
        col_width = (758 - 2*MARGIN_X) // 3

        for i, f in enumerate(future_forecasts):
            cond = f["condition"]
            temp = f["temperature"]
            time_label = f["datetime"].split("T")[1][:5]

            # X position for this column
            x_col = MARGIN_X + i * col_width

            # --- ICON ---
            icon_name = ICON_MAP.get(cond, "wi-na.png")
            icon_path = f"/share/kindle/icons/{icon_name}"
            if os.path.exists(icon_path):
                try:
                    icon_h = Image.open(icon_path).convert("RGBA").resize((ICON_SMALL, ICON_SMALL))
                    img.paste(icon_h, (x_col + (col_width - ICON_SMALL)//2, y), icon_h)
                except:
                    pass

            # --- TIME LABEL ---
            bbox = draw.textbbox((0, 0), time_label, font=font_text)
            time_w = bbox[2] - bbox[0]
            draw.text((x_col + (col_width - time_w) // 2, y + ICON_SMALL + 5), time_label, font=font_text_small, fill=0)

            # --- TEMPERATURE LABEL ---
            temp_str = f"{temp}°C"
            bbox = draw.textbbox((0, 0), temp_str, font=font_text_small)
            temp_w = bbox[2] - bbox[0]
            draw.text((x_col + (col_width - temp_w) // 2, y + ICON_SMALL + 25), temp_str, font=font_text_small, fill=0)

        # Move Y for next section
        y += ICON_SMALL + 45


        # --- WEATHER TOMORROW ---
        if tomorrow_forecast:
            y += SECTION_SPACING
            title = "Weather Tomorrow"
            draw.text((MARGIN_X, y), title, font=font_text, fill=0)
            bbox = draw.textbbox((MARGIN_X, y), title, font=font_text)
            text_bottom = bbox[3]
            draw.line((MARGIN_X, text_bottom + 5, 758 - MARGIN_X, text_bottom + 5), fill=LINE_FILL, width=LINE_WIDTH)

            y += 35

            # Extract fields from Buienradar
            cond_tomorrow = tomorrow_forecast.get("condition", "sunny") # Only one from Open-Meteo, strangely I can't get the one from Buienradar to work
            cond_detailed_tomorrow = self.get_state("sensor.buienradar_full_condition_1d")
            temp_min = self.get_state("sensor.buienradar_minimum_temperature_1d")
            temp_max = self.get_state("sensor.buienradar_temperature_1d")
            rainchance = self.get_state("sensor.buienradar_rainchance_1d")
            sunrise_raw = self.get_state("sensor.sun_next_rising")
            sunset_raw = self.get_state("sensor.sun_next_setting")

            draw.text((MARGIN_X, y), f"{cond_detailed_tomorrow}", font=font_text_small, fill=0)
            y += 25
            draw.text((MARGIN_X, y), f"Min {temp_min}°C / Max {temp_max}°C", font=font_text, fill=0)
            y += 30

            # Rain
            draw.text((MARGIN_X, y), f"Rain: {rainchance}%", font=font_text, fill=0)
            y += 30

            # Sunrise / Sunset
            if sunrise_raw and sunset_raw:
                sunrise_dt = datetime.fromisoformat(sunrise_raw.replace("Z", "+00:00")).astimezone(tz)
                sunset_dt = datetime.fromisoformat(sunset_raw.replace("Z", "+00:00")).astimezone(tz)

                sunrise_fmt = sunrise_dt.strftime("%H:%M")
                sunset_fmt = sunset_dt.strftime("%H:%M")

                draw.text((MARGIN_X, y), f"Sunrise {sunrise_fmt} – Sunset {sunset_fmt}", font=font_text, fill=0)
                y += 30

            # Weather icon
            icon_tomorrow = ICON_MAP.get(cond_tomorrow, "wi-na.png")
            icon_path = f"/share/kindle/icons/{icon_tomorrow}"
            if os.path.exists(icon_path):
                try:
                    icon2 = Image.open(icon_path).convert("RGBA").resize((ICON_SIZE, ICON_SIZE))
                    img.paste(icon2, (758 - ICON_SIZE - MARGIN_X, y - 120), icon2)
                except:
                    pass


        # --- TWO-COLUMN LAYOUT ---
        y += 20

        # --- COLUMN 1 - INDOOR CLIMATE ---
        title = "Indoor Climate"
        draw.text((LEFT_X, y), title, font=font_text, fill=0)
        bbox = draw.textbbox((LEFT_X, y), title, font=font_text)
        text_bottom = bbox[3]
        draw.line((LEFT_X, text_bottom + 5, RIGHT_X - 20, text_bottom + 5), fill=LINE_FILL, width=LINE_WIDTH)

        y_left = y + 35
        draw.text((LEFT_X, y_left), f"Living Room: {temp_living}°C | {humidity_living}% RH", font=font_text, fill=0)
        y_left += 30

        # Two-column layout for small room temperatures
        col_gap = 180  # horizontal space between the two columns

        # First row
        draw.text((LEFT_X, y_left), f"Entrance: {temp_entrance}°C", font=font_text_small, fill=0)
        draw.text((LEFT_X + col_gap, y_left), f"Bedroom: {temp_bedroom}°C", font=font_text_small, fill=0)

        # Second row
        y_left += 25
        draw.text((LEFT_X, y_left), f"Bathroom: {temp_bathroom}°C", font=font_text_small, fill=0)
        draw.text((LEFT_X + col_gap, y_left), f"Office: {temp_office}°C", font=font_text_small, fill=0)

        # --- COLUMN 2 - AIR QUALITY ---
        title = "Air Quality"
        draw.text((RIGHT_X, y), title, font=font_text, fill=0)
        bbox = draw.textbbox((RIGHT_X, y), title, font=font_text)
        text_bottom = bbox[3]
        draw.line((RIGHT_X, text_bottom + 5, 758 - MARGIN_X, text_bottom + 5), fill=LINE_FILL, width=LINE_WIDTH)
        y_right = y + 35
        draw.text((RIGHT_X, y_right), f"PM2.5 Index: {aqi_pm25}", font=font_text_small, fill=0)
        y_right += 25
        draw.text((RIGHT_X, y_right), f"CO2: {aqi_co2} ppm", font=font_text_small, fill=0)

        y = max(y_left, y_right) + 50


        # --- WASTE COLLECTION ---
        title = "Waste Collection"
        draw.text((MARGIN_X, y), title, font=font_text, fill=0)
        bbox = draw.textbbox((MARGIN_X, y), title, font=font_text)
        text_bottom = bbox[3]
        draw.line((MARGIN_X, text_bottom + 5, 758 - MARGIN_X, text_bottom + 5), fill=LINE_FILL, width=LINE_WIDTH)

        y += 40

        # Sensors + labels
        waste_sensors = [
            ("sensor.residual_household_waste", "Residual Waste"),
            ("sensor.pmd", "PMD"),
            ("sensor.paper_cardboard", "Paper/Cardboard")
        ]

        # 3 equal columns
        col_width = (758 - 2*MARGIN_X) // 3

        for i, (entity, label) in enumerate(waste_sensors):
            x_col = MARGIN_X + i * col_width

            # --- LABEL ABOVE DATE ---
            bbox = draw.textbbox((0, 0), label, font=font_text)
            label_w = bbox[2] - bbox[0]
            draw.text((x_col + (col_width - label_w) // 2, y), label, font=font_text, fill=0)

            # --- DATE ---
            raw = self.get_state(entity)
            try:
                dt = datetime.strptime(raw, "%d/%m/%Y")
                formatted = dt.strftime("%a %d %b")
            except:
                formatted = "-"

            bbox = draw.textbbox((0, 0), formatted, font=font_text)
            date_w = bbox[2] - bbox[0]
            draw.text((x_col + (col_width - date_w) // 2, y + 25), formatted, font=font_text, fill=0)

        # Move Y for next section
        y += 80


        # --- SAVE ---
        #self.log("Saving Kindle display image...", level="INFO")
        try:
            img.save(self.args["output_path"])
            self.log("Kindle display image updated.", level="INFO")
        except Exception as e:
            self.log(f"ERROR saving image: {e}", level="ERROR")
