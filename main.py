from typing import Optional

import numpy as np
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image

from sd.generate import PIPELINE_NAMES, MODEL_VERSIONS, generate

DEFAULT_PROMPT = "border collie puppy"
DEFAULT_WIDTH, DEFAULT_HEIGHT = 512, 512
OUTPUT_IMAGE_KEY = "output_img"
LOADED_IMAGE_KEY = "loaded_image"


def get_image(key: str) -> Optional[Image.Image]:
    if key in st.session_state:
        return st.session_state[key]
    return None


def set_image(key: str, img: list[Image.Image]):
    st.session_state[key] = img


def prompt_and_generate_button(prefix, pipeline_name: PIPELINE_NAMES, **kwargs, ):
    prompt = st.text_area(
        "Prompt",
        value=DEFAULT_PROMPT,
        key=f"{prefix}-prompt",
    )
    negative_prompt = st.text_area(
        "Negative prompt",
        value="",
        key=f"{prefix}-negative-prompt",
    )
    
    steps = st.slider(
            "Number of inference steps",
            min_value=1,
            max_value=200,
            value=20,
            key=f"{prefix}-inference-steps",
        )
    guidance_scale = st.slider(
            "Guidance scale",
            min_value=0.0,
            max_value=20.0,
            value=7.5,
            step=0.5,
            key=f"{prefix}-guidance-scale",
        )
    num_images = st.slider(
            "Number of generated images",
            min_value=1,
            max_value=6,
            value=1,
            step=1,
            key=f"{prefix}-generated-number",
        )

    enable_attention_slicing = st.checkbox(
        "Enable attention slicing (enables higher resolutions but is slower)",
        key=f"{prefix}-attention-slicing",
    )
    enable_cpu_offload = st.checkbox(
        "Enable CPU offload (if you run out of memory, e.g. for XL model)",
        key=f"{prefix}-cpu-offload",
        value=False,
    )
    if st.button("Generate image", key=f"{prefix}-btn"):
        with st.spinner("Generating image..."):
            image = generate(
                prompt,
                pipeline_name,
                negative_prompt=negative_prompt,
                steps=steps,
                guidance_scale=guidance_scale,
                enable_attention_slicing=enable_attention_slicing,
                enable_cpu_offload=enable_cpu_offload,
                num_images=num_images,
                **kwargs,
            )
            set_image(OUTPUT_IMAGE_KEY, image)
        
                



def width_and_height_sliders(prefix):
    col1, col2 = st.columns(2)
    with col1:
        width = st.slider(
            "Width",
            min_value=64,
            max_value=1600,
            step=16,
            value=768,
            key=f"{prefix}-width",
        )
    with col2:
        height = st.slider(
            "Height",
            min_value=64,
            max_value=1600,
            step=16,
            value=768,
            key=f"{prefix}-height",
        )
    return width, height


def image_uploader(prefix):
    image = st.file_uploader("Image", ["jpg", "png"], key=f"{prefix}-uploader")
    if image:
        image = Image.open(image)
        print(f"loaded input image of size ({image.width}, {image.height})")
        return image

    return get_image(LOADED_IMAGE_KEY)


def inpainting():
    image = image_uploader("inpainting")

    if not image:
        return None, None

    brush_size = st.number_input("Brush Size", value=50, min_value=1, max_value=100)

    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0.0)",
        stroke_width=brush_size,
        stroke_color="#FFFFFF",
        background_color="#000000",
        background_image=image,
        update_streamlit=True,
        height=image.height*1.1,
        width=image.width*1.1,
        drawing_mode="freedraw",
        key="inpainting-canvas",
    )

    if not canvas_result or canvas_result.image_data is None:
        return None, None

    mask = canvas_result.image_data
    mask = mask[:, :, -1] > 0
    if mask.sum() > 0:
        mask = Image.fromarray(mask)
        st.image(mask)
        return image, mask

    return None, None


def txt2img_tab():
    prefix = "txt2img"
    width, height = width_and_height_sliders(prefix)
    version = st.selectbox("Model version", ["2.1", "XL 1.0","Turbo"], key=f"{prefix}-version")
    st.markdown(
        "**Note**: XL 1.0 is slower and requires more memory. You can use CPU offload to reduce memory usage. You can refine the image afterwards with img2img"
    )
    result = prompt_and_generate_button(
        prefix, "txt2img", width=width, height=height, version=version
    )
    return result


def inpainting_tab():
    prefix = "inpaint"
    col1, col2 = st.columns(2)

    with col1:
        image_input, mask_input = inpainting()

    with col2:
        if image_input and mask_input:
            version = st.selectbox(
                "Model version", ["2.0", "XL 1.0"], key="inpaint-version"
            )
            strength = st.slider(
                "Strength of inpainting (1.0 essentially ignores the masked area of the original input image)",
                min_value=0.0,
                max_value=1.0,
                value=1.0,
                step=0.05,
                key=f"{prefix}-strength",
            )
            result = prompt_and_generate_button(
                prefix,
                "inpaint",
                image_input=image_input,
                mask_input=mask_input,
                version=version,
                strength=strength,
            )
            return result


def img2img_tab():
    prefix = "img2img"
    col1, col2 = st.columns(2)

    with col1:
        image = image_uploader(prefix)
        if image:
            st.image(image)

    with col2:
        if image:
            version = st.selectbox(
                "Model version", ["2.1", "XL 1.0 refiner"], key=f"{prefix}-version"
            )
            strength = st.slider(
                "Strength (1.0 ignores the existing image so it's not a useful value)",
                min_value=0.0,
                max_value=1.0,
                value=0.3,
                step=0.05,
                key=f"{prefix}-strength",
            )
            result = prompt_and_generate_button(
                prefix, "img2img", image_input=image, version=version, strength=strength
            )
            return result

def display_output():
    output_image = get_image(OUTPUT_IMAGE_KEY)
    if output_image:
        
        st.write('Your image has been generated!', icon='🎇')
        num_images = len(output_image)
        images_per_row = 2  # Number of images to display per row
        rows = num_images // images_per_row + (num_images % images_per_row > 0)  # Calculate number of rows

        for i in range(rows):
            row_images = output_image[i * images_per_row: (i + 1) * images_per_row]
            cols = st.columns(len(row_images))  # Create columns for each image in the row
            for col, image in zip(cols, row_images):
                with col:
                    with st.container():
                        st.image(image, use_column_width=True)
                        
    else:
        st.markdown("")
        
def main():
    st.set_page_config(layout="wide")
    st.title("Stablity AI Playground \nBring your imagnination to the ground.")
    col1, col2 = st.columns([2,1])
    
    with col1:
        tab1, tab2, tab3 = st.tabs(
            ["Text to Image (txt2img)", "Inpainting", "Image to image (img2img)"]
        )
        
        with tab1:
            txt2img_tab()
                
        with tab2:
            inpainting_tab()

        with tab3:
            img2img_tab()
    with col2:
        display_output()
    
if __name__ == "__main__":
    main()
