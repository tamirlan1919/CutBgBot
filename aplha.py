from PIL import Image, ImageOps


def add_alpha_border(image, min_dimension=450):
    width, height = image.size

    new_width = max(width, min_dimension)
    new_height = max(height, min_dimension)


    new_image = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))

    new_image.paste(image, ((new_width - width) // 2, (new_height - height) // 2))
    return new_image

def add_alpha_border_second(image, expansion_factor=2):
    width, height = image.size

    # Calculate minimum dimensions to achieve at least 1.5 times expansion
    min_width = int(width * expansion_factor)
    min_height = int(height * expansion_factor)

    # Calculate required border sizes to achieve these dimensions
    border_width = (min_width - width) // 2
    border_height = (min_height - height) // 2

    # Create a new image with a transparent background that meets minimum dimensions
    new_image = Image.new("RGBA", (min_width, min_height), (0, 0, 0, 0))

    # Paste the original image into the center of the new image
    new_image.paste(image, (border_width, border_height))

    return new_image

def process_image_with_alpha_border_second(pil_image):
    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")
    pil_image = add_alpha_border_second(pil_image)
    return pil_image

def process_image_with_alpha_border(pil_image):
    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")
    pil_image = add_alpha_border(pil_image)
    return pil_image