"""
A script that compile the resources used in the project.
Must be called from the root project folder and python must be in your path.

if "--commands" is passed to the script, the script will output the commands used WITHOUT executing them.
This is usefull if you only want to compile a certain asset

"""

from pathlib import Path
import subprocess, shutil, sys

# Testing if we are in the project root
if not Path('./assets/').is_dir():
    raise ValueError("This script must be started from the project root dir")

COMPILE_SHADER_PATH = "./tools/compile_shaders.py"
COMPRESS_IMAGES_PATH = "./tools/compress_images.py"
KTX_MERGE_PATH = "./tools/ktxmerge.py"

SHADERS_PATH = Path("./assets/shaders")
IMAGES_PATH = Path("./assets/images")
MODELS_PATH = Path("./assets/models")

ONLY_COMMANDS = "--commands" in sys.argv

MAX_SUBPROCESSES = 5
OUTPUT = ""

def wait_subprocesses(outputs):
    global OUTPUT

    if ONLY_COMMANDS:
        return

    print(f"WAITING FOR {tuple(outputs.keys())}")

    for name, process in outputs.items():
        OUTPUT += f"\n{name}\n" + (process.communicate()[0]).decode("utf8")

    outputs.clear()

def process(*inputs):
    global OUTPUT

    if ONLY_COMMANDS:
        OUTPUT += " ".join(inputs) + "\n"
    else:
        return subprocess.Popen(inputs, stdout=subprocess.PIPE)


shaders = (
    (SHADERS_PATH/"debug_texture", "debug_texture"),
    (SHADERS_PATH/"debug_texture_array", "debug_texture_array"),
    (SHADERS_PATH/"debug_texture_cube", "debug_texture_cube"),
    (SHADERS_PATH/"pbr", "pbr"),
)


images = (
    (IMAGES_PATH/"dev/", "vulkan_logo.jpg"),
    (IMAGES_PATH/"dev/array_test", "*.png"),
    (MODELS_PATH/"dev/damaged_helmet", "damaged_helmet_*.jpg", "--miplevels", "100"),
)


images_merge_copy = (
    ("MOVE", IMAGES_PATH/"dev/vulkan_logo.ktx", IMAGES_PATH/"vulkan_logo.ktx"),
    ("COPY", IMAGES_PATH/"dev/unity_gareout/brdf_ue4.bin", IMAGES_PATH/"unity_gareout/brdf_ue4.bin"),
    ("COPY", IMAGES_PATH/"dev/unity_gareout/specular_cubemap_ue4_256_luv.bin", IMAGES_PATH/"unity_gareout/specular_luv.bin"),
    ("MERGE_ARRAY", IMAGES_PATH/"dev/array_test/*", IMAGES_PATH/"array_test.ktx"),
    ("MERGE_ARRAY", MODELS_PATH/"dev/damaged_helmet/damaged_helmet_*", IMAGES_PATH/"damaged_helmet.ktx"),
)

clean = (
    (IMAGES_PATH/"dev/array_test/", "*.ktx"),
    (MODELS_PATH/"dev/damaged_helmet/", "*.ktx"),
)


#
# SHADERS!
#
shaders_outputs = {}
for shader_path, shader_name in shaders:
    p = process("python", COMPILE_SHADER_PATH, "--path", str(shader_path), "--input", shader_name)
    if p is not None:
        shaders_outputs[f"[SHADER {shader_name}]"] = p 

    if len(shaders_outputs) > MAX_SUBPROCESSES:
        wait_subprocesses(shaders_outputs)

wait_subprocesses(shaders_outputs)

#
# IMAGES!
#
images_outputs = {}
for image_path, image_name , *extra in images:
    p = process("python", COMPRESS_IMAGES_PATH, "--path", str(image_path), "--input", image_name, *extra)
    if p is not None:
        images_outputs[f"[IMAGE {image_path}/{image_name}]"] = p 

    if len(images_outputs) > MAX_SUBPROCESSES:
        wait_subprocesses(images_outputs)

wait_subprocesses(images_outputs)

#
# IMAGES MERGING & MOVING!
#
merge_outputs = {}
for action, target, output in images_merge_copy:
    p = None

    if action == "MOVE" and not ONLY_COMMANDS:
        shutil.move(target, output)
    elif action == "COPY" and not ONLY_COMMANDS:
        shutil.copy(target, output)
    elif action == "MERGE_ARRAY":
        p = process("python", KTX_MERGE_PATH,  "--array", "--auto", "--output", str(output), "--input", str(target))
    elif action == "MERGE_CUBE":
        p = process("python", KTX_MERGE_PATH,  "--cube", "--auto", "--output", str(output), "--input", str(target))
    elif action == "MERGE_CUBE_MIPS":
        p = process("python", KTX_MERGE_PATH,  "--cube", "--auto", "--mipmaps", "--output", str(output), "--input", str(target))

    if p is not None:
        merge_outputs[f"[{action} {target}]"] = p 

    if len(merge_outputs) > MAX_SUBPROCESSES:
        wait_subprocesses(merge_outputs)

wait_subprocesses(merge_outputs)

#
# IMAGE CLEANING!
#

if not ONLY_COMMANDS:
    for path, pattern in clean:
        for path in path.glob(pattern):
            path.unlink()

#
# Printing outputs
#

print()
print(OUTPUT)
