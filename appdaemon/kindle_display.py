import appdaemon.plugins.hass.hassapi as hass
from PIL import Image, ImageDraw, ImageFont
import datetime
import os


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
MARGIN_X = 45
MARGIN_Y = 35
LINE_WIDTH_HEADER = 2
LINE_WIDTH = 1
LINE_FILL_HEADER = 80
LINE_FILL = 120
LINE_FILL_LIGHT = 180
SECTION_SPACING = 25
ICON_SIZE = 94
ICON_SMALL = 60

font_header = ImageFont.truetype("/config/www/fonts/NotoSans-Bold.ttf", 24)
font_text = ImageFont.truetype("/config/www/fonts/NotoSans-Regular.ttf", 18)
font_text_small = ImageFont.truetype("/config/www/fonts/NotoSans-Regular.ttf", 16)
font_emoji = ImageFont.truetype("/config/www/fonts/Twemoji.Mozilla.ttf", 18)

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
        # Then every hour at :00 and :30
        now = datetime.datetime.now()
        next_full = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
        next_half = now.replace(minute=30, second=0, microsecond=0)
        if now.minute >= 30:
            next_half += datetime.timedelta(hours=1)

        self.run_hourly(self.update_display, next_full)
        self.run_hourly(self.update_display, next_half)


    def update_display(self, kwargs):
        now = datetime.datetime.now()
        hour = now.hour

        # --- WEATHER ---
        weather_state = self.get_state("weather.irm")
        weather_temp = self.get_state("weather.irm", attribute="temperature")
        # weather_humidity = self.get_state("weather.irm", attribute="humidity")
        weather_uv = self.get_state("weather.irm", attribute="uv_index")


        # --- FORECAST ---
        #forecast = self.get_state("weather.openweathermap_forecast", attribute="forecast")
        raw = self.call_service(
            "weather/get_forecasts",
            entity_id="weather.open_meteo",
            type="hourly"
        )
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
        aqi_summary = self.get_state("sensor.aqi_summary")
        aqi_pm25 = self.get_state("sensor.healthy_home_coach_air_quality")
        aqi_co2 = self.get_state("sensor.healthy_home_coach_carbon_dioxide_sensor")

        # --- IMAGE SETUP ---
        img = Image.new("L", (758, 1024), 255)
        draw = ImageDraw.Draw(img)


        # --- HEADER ---
        title = "Home Status"
        refresh = f"Last refresh: {now.strftime('%Y-%m-%d %H:%M')}"
        draw.text((MARGIN_X, MARGIN_Y), title, font=font_header, fill=0)
        bbox = draw.textbbox((0, 0), refresh, font=font_text)
        refresh_width = bbox[2] - bbox[0]
        draw.text((758 - refresh_width - MARGIN_X, MARGIN_Y), refresh, font=font_text, fill=0)
        draw.line((MARGIN_X, MARGIN_Y + 35, 758 - MARGIN_X, MARGIN_Y + 35), fill=LINE_FILL_HEADER, width=LINE_WIDTH_HEADER)

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
        draw.text((MARGIN_X, y + 30), f"UV: {uv_cat} ({weather_uv})", font=font_text, fill=0)


        # Icon today
        icon_today = ICON_MAP.get(weather_state, "wi-na.png")
        icon_path = f"/config/www/kindle/icons/{icon_today}"
        if os.path.exists(icon_path):
            try:
                icon = Image.open(icon_path).convert("RGBA").resize((ICON_SIZE, ICON_SIZE))
                img.paste(icon, (758 - ICON_SIZE - MARGIN_X, y - 10), icon)
            except Exception as e:
                self.log(f"Icon error: {e}", level="WARNING")

        # --- HOURLY FORECAST ---
        #y += 120
        #draw.text((MARGIN_X, y), "Next Hours", font=font_text, fill=0)
        #draw.line((MARGIN_X, y + 20, 758 - MARGIN_X, y + 20), fill=LINE_FILL, width=LINE_WIDTH)
        #y += 35

        #for f in hourly_forecasts:
        #    cond = f["condition"]
        #    temp = f["temperature"]
        #    time_label = f["datetime"].split("T")[1][:5]

        #    draw.text((MARGIN_X, y), f"{time_label} – {temp}°C – {cond}", font=font_text, fill=0)

        #    icon_name = ICON_MAP.get(cond, "wi-na.png")
        #    icon_path = f"/config/www/kindle/icons/{icon_name}"
        #    if os.path.exists(icon_path):
        #        try:
        #            icon_h = Image.open(icon_path).convert("RGBA").resize((ICON_SMALL, ICON_SMALL))
        #            img.paste(icon_h, (758 - ICON_SMALL - MARGIN_X, y - 5), icon_h)
        #        except:
        #            pass

        #    y += 40

        # --- NEXT HOURS GRAPH ---
        y += 80
        title = "Next Hours"
        draw.text((MARGIN_X, y), title, font=font_text, fill=0)
        bbox = draw.textbbox((MARGIN_X, y), title, font=font_text)
        text_bottom = bbox[3]
        draw.line((MARGIN_X, text_bottom + 5, 758 - MARGIN_X, text_bottom + 5), fill=LINE_FILL, width=LINE_WIDTH)


        y += 40

        # Extract temperatures and labels
        temps = [f["temperature"] for f in hourly_forecasts]
        labels = [f["datetime"].split("T")[1][:5] for f in hourly_forecasts]
        conds = [f["condition"] for f in hourly_forecasts]

        # Graph dimensions
        graph_x1 = MARGIN_X + 60
        graph_x2 = 758 - MARGIN_X - 60
        graph_y1 = y
        graph_y2 = y + 120

        # Base line
        draw.line((graph_x1, graph_y2, graph_x2, graph_y2), fill=LINE_FILL_LIGHT, width=LINE_WIDTH)


        # Normalize temperatures
        t_min = min(temps)
        t_max = max(temps)
        t_range = max(1, t_max - t_min)

        # Compute X positions
        step = (graph_x2 - graph_x1) // (len(temps) - 1)
        points = []

        for i, t in enumerate(temps):
            x = graph_x1 + i * step
            # invert Y because top = low temp
            y_t = graph_y2 - int((t - t_min) / t_range * (graph_y2 - graph_y1 - 20))
            points.append((x, y_t))

        # Draw lines
        for i in range(len(points) - 1):
            draw.line((points[i][0], points[i][1], points[i+1][0], points[i+1][1]), fill=0, width=2)

        # Draw points
        for x, y_t in points:
            draw.ellipse((x - 4, y_t - 4, x + 4, y_t + 4), fill=0)

        # Draw labels and icons
        for i, (x, t, label, cond) in enumerate(zip([p[0] for p in points], temps, labels, conds)):
            # Temperature label
            draw.text((x - 10, graph_y2 + 10), f"{t}°", font=font_text_small, fill=0)

            # Time label
            draw.text((x - 15, graph_y2 + 30), label, font=font_text_small, fill=0)

            # Weather icon above point
            icon_name = ICON_MAP.get(cond, "wi-na.png")
            icon_path = f"/config/www/kindle/icons/{icon_name}"
            if os.path.exists(icon_path):
                try:
                    icon_h = Image.open(icon_path).convert("RGBA").resize((40, 40))
                    img.paste(icon_h, (x - 20, graph_y1 - 10), icon_h)
                except:
                    pass

        # Move Y for next section
        y = graph_y2 + 60


        # --- WEATHER TOMORROW ---
        if hour >= 18 and tomorrow_forecast:
            y += SECTION_SPACING
            title = "Weather Tomorrow"
            draw.text((MARGIN_X, y), title, font=font_text, fill=0)
            bbox = draw.textbbox((MARGIN_X, y), title, font=font_text)
            text_bottom = bbox[3]
            draw.line((MARGIN_X, text_bottom + 5, 758 - MARGIN_X, text_bottom + 5), fill=LINE_FILL, width=LINE_WIDTH)

            y += 35
            cond_tomorrow = tomorrow_forecast.get("condition", "sunny")
            temp_tomorrow = tomorrow_forecast.get("temperature", "?")

            draw.text((MARGIN_X, y), f"{temp_tomorrow}°C – {cond_tomorrow}", font=font_text, fill=0)

            icon_tomorrow = ICON_MAP.get(cond_tomorrow, "wi-na.png")
            icon_path = f"/config/www/kindle/icons/{icon_tomorrow}"
            if os.path.exists(icon_path):
                try:
                    icon2 = Image.open(icon_path).convert("RGBA").resize((ICON_SIZE, ICON_SIZE))
                    img.paste(icon2, (758 - ICON_SIZE - MARGIN_X, y - 10), icon2)
                except:
                    pass

        # --- INDOOR CLIMATE ---
        y += 120
        title = "Indoor Climate"
        draw.text((MARGIN_X, y), title, font=font_text, fill=0)
        bbox = draw.textbbox((MARGIN_X, y), title, font=font_text)
        text_bottom = bbox[3]
        draw.line((MARGIN_X, text_bottom + 5, 758 - MARGIN_X, text_bottom + 5), fill=LINE_FILL, width=LINE_WIDTH)

        y += 35
        draw.text((MARGIN_X, y), f"Living Room: {temp_living}°C | {humidity_living}% RH", font=font_text, fill=0)
        y += 30
        draw.text((MARGIN_X, y), f"Entrance: {temp_entrance}°C", font=font_text, fill=0)
        y += 30
        draw.text((MARGIN_X, y), f"Bedroom: {temp_bedroom}°C", font=font_text, fill=0)
        y += 30
        draw.text((MARGIN_X, y), f"Bathroom: {temp_bathroom}°C", font=font_text, fill=0)
        y += 30
        draw.text((MARGIN_X, y), f"Office: {temp_office}°C", font=font_text, fill=0)

        # --- AIR QUALITY ---
        y += 80
        title = "Air Quality"
        draw.text((MARGIN_X, y), title, font=font_text, fill=0)
        bbox = draw.textbbox((MARGIN_X, y), title, font=font_text)
        text_bottom = bbox[3]
        draw.line((MARGIN_X, text_bottom + 5, 758 - MARGIN_X, text_bottom + 5), fill=LINE_FILL, width=LINE_WIDTH)
        y += 35

        summary = aqi_summary or ""
        emoji_char = ""
        text_part = summary
        if summary and ord(summary[0]) > 1000:
            emoji_char = summary[0]
            text_part = summary[1:].strip()
        if emoji_char:
            draw.text((MARGIN_X, y), emoji_char, font=font_emoji, fill=0)
            draw.text((MARGIN_X + 30, y), text_part, font=font_text, fill=0)
        else:
            draw.text((MARGIN_X, y), summary, font=font_text, fill=0)
        y += 30
        draw.text((MARGIN_X, y), f"PM2.5 Index: {aqi_pm25}", font=font_text, fill=0)
        y += 30
        draw.text((MARGIN_X, y), f"CO2: {aqi_co2} ppm", font=font_text, fill=0)


        # --- SAVE ---
        self.log("Saving Kindle display image...", level="INFO")
        try:
            img.save(self.args["output_path"])
            self.log("Kindle display image updated.", level="INFO")
        except Exception as e:
            self.log(f"ERROR saving image: {e}", level="ERROR")
