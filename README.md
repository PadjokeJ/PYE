# PYE -- Academic Management Tool

A website that allows for academic management. 

## Deployment

In order for the service to start, you need a `.env` file, in order to get started with a base, you can copy `dev.env`
```bash
cp dev.env .env
```
You can then launch the service using docker
```bash
docker compose build && docker compose up
```

Make sure to change the default values from `dev.env`!

