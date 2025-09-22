from django.shortcuts import render

# Main view to handle Education & Awareness page
def education_awareness(request):
    context = {
        "guidelines": get_guidelines(),
        "videos": get_videos(),
        "tips": get_tips(),
    }
    return render(request, 'education_awareness.html', context)

# Function to retrieve guidelines and articles
def get_guidelines():
    return [
        {
            "title": "Complete Waste Segregation Guide",
            "time": "10 mins read",
            "downloads": 450,
            "categories": ["Plastic", "Paper", "E-waste", "Metal", "Glass"],
            "description": "Learn to separate different types of waste correctly to maximize recycling efficiency.",
            "image": "/path/to/image1.jpg",  # Replace with actual image URL
        },
        {
            "title": "The Economic and Social Benefits of Recycling",
            "time": "5 mins read",
            "downloads": 200,
            "categories": ["Carbon footprint", "Green jobs", "Landfill Reduction"],
            "description": "Learn how an increase in recycling rates leads to reduced burdens on landfills and long-term cost savings.",
            "image": "/path/to/image2.jpg",  # Replace with actual image URL
        },
    ]

# Function to retrieve videos
def get_videos():
    return [
        {
            "title": "How to Segregate Waste for Recycling",
            "duration": "3 mins",
            "views": 1000,
            "description": "A quick guide to waste segregation and its importance for the environment.",
            "image": "/path/to/video_image1.jpg",  # Replace with actual image URL
            "url": "https://www.youtube.com/watch?v=example1",
        },
        {
            "title": "The Importance of Recycling",
            "duration": "7 mins",
            "views": 1500,
            "description": "Why recycling is crucial for our planet and how it can help combat climate change.",
            "image": "/path/to/video_image2.jpg",  # Replace with actual image URL
            "url": "https://www.youtube.com/watch?v=example2",
        },
    ]

# Function to retrieve quick tips
def get_tips():
    return [
        {
            "title": "Recycling Tip #1: Sorting is Key",
            "description": "Make sure to separate plastics, paper, glass, and metal to avoid contamination.",
        },
        {
            "title": "Recycling Tip #2: Don't Bag Your Recyclables",
            "description": "Keep your recyclables loose and not in plastic bags to make sorting easier.",
        },
    ]
