# Project 7: NASA API - Space Explorer App
NASA releases a new "Astronomy Picture of the Day" (APOD) every day—spotlighting breathtaking images of galaxies, stars, planets, and more.

Your task is to build an interactive web app that fetches and displays these photos using [NASA's API](https://api.nasa.gov/). Users will pick a date range and instantly view stunning photos from across the cosmos, along with titles and descriptions.

You'll get to use your skills to build something that's actually connected to real-world data from one of the most iconic organizations in the world.

## Starter Files
- The provided files include a NASA logo, date inputs, a button, a placeholder for your gallery, and basic layout and styling to help you get started.
- It also includes built-in logic (in `dateRange.js`) to handle the valid APOD date range—from June 16, 1995 to today. No need to modify it.
- All your custom JavaScript should go in `script.js`. That's where you'll write the code that fetches data and displays your gallery.

## Run the App
The local server proxies NASA's APOD API, repairs placeholder image URLs, and falls back to NASA's public archive if the API rate limit is reached. Start it with:

```bash
python3 server.py
```

Then open http://localhost:8000. The server uses NASA's `DEMO_KEY` by default. To use your own key, set `NASA_API_KEY` before starting the server:

```bash
NASA_API_KEY=your_api_key python3 server.py
```
