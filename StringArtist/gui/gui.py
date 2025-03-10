import functools
import json
import logging
import math
import tkinter as tk
import tkinter.filedialog
from pathlib import Path
from tkinter import messagebox

from PIL import Image, ImageTk
from typing import Union

from StringArtist.config import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    WINDOW_TITLE,
    WORKSPACE_PADDING,
    ICON,
)

logger = logging.getLogger("gui.py")


def default_btn_callback(*args, **kwargs):
    logger.warning(f"Unused button! {args}, {kwargs}")


TOOLS = [
    "Nail",
    "Erase",
    "Prioritize",
    "Export Positions",
    "Import Positions",
    "Background",
]


def scale_to_fit(image: Image.Image, x: int, y: int) -> Image.Image:
    """
    Scales the image to fit within a box of dimensions of the canvas while maintaining aspect ratio.

    :param image: A PIL Image
    :param x: Maximum width of the bounding box
    :param y: Maximum height of the bounding box
    :return: A new resized PIL Image instance.
    """
    image.thumbnail((x, y), Image.LANCZOS)
    return image


class GUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.title(WINDOW_TITLE)
        self.root.iconbitmap(ICON)
        self.root.tk_setPalette(
            background="#f0f0f0",
            foreground="black",
            activeBackground="#ececec",
            activeForeground="black",
        )

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        self.toolbar_widgets: list = []
        self.selected_tool = -1

        self.workspace_frame: Union[tk.Frame, None] = None
        self.workspace_canvas: Union[tk.Canvas, None] = None

        self.working_im: Union[Image, None] = None
        self.im_path: Union[str, None] = None
        self.im_scale: float = 1

        self.draw_toolbar()
        self.draw_workspace()

        self.placements: list[list[int, int, bool]] = []
        self.priority_nail: int = 0

    @property
    def active_tool(self) -> str | None:
        """
        Converts self.selected_tool to the tool in the TOOLS constant, returns None if no tool is selected
        :return: str | None
        """

        if self.selected_tool == -1:
            return None

        return TOOLS[self.selected_tool]

    def tool_select_callback(self, idx: int) -> None:
        """
        The callback to handle selecting a new tool
        :param idx: The index of the tool selected
        :return:
        """

        if TOOLS[idx] == "Background":
            return self.background_tool_callback()
        elif TOOLS[idx] == "Export Positions":
            return self.export_positions_callback()
        elif TOOLS[idx] == "Import Positions":
            return self.import_positions_callback()

        old_btn = (
            self.toolbar_widgets[self.selected_tool]
            if self.selected_tool != -1
            else None
        )

        if old_btn is not None:
            old_btn.configure(background="#F0F0F0")

        self.selected_tool = idx
        btn = self.toolbar_widgets[self.selected_tool]

        btn.configure(background="#dbdbdb")

    def export_positions_callback(self) -> None:
        """
        The callback for exporting nail positions
        :return: None
        """

        if len(self.placements) < 3:
            messagebox.showinfo(
                "Not Enough Points",
                f"Need at least 3 nail positions to be able to export",
            )
            return

        data = list(map(lambda x: [x[0], x[1], int(x[2])], self.placements))
        path = str(self.im_path) + ".placements.json"

        logger.info(f"Exporting positions to {path!r}")

        with open(path, "w") as f:
            json.dump(data, f)

        messagebox.showinfo("File Saved", f"File saved to {path}")

    def import_positions_callback(self) -> None:
        """
        The callback for importing placements back into the program
        :return: None
        """
        path = Path(tk.filedialog.askopenfilename())
        if not path.is_file():
            messagebox.showinfo("Import Error", f"Couldn't find file {path}!")
            return

        self.im_path = str(path).rstrip(".placements.json")

        with open(path, "rb") as f:
            placements = json.load(f)

        # validate file
        if not isinstance(placements, list):
            logger.info("JSON contains invalid type!")
            messagebox.showinfo("Import Error", "Invalid file")
            return

        new_placements: list[list[int, int, bool]] | list = []

        for i in placements:
            if not isinstance(i, list):
                logger.info("JSON contains invalid type!")
                messagebox.showinfo("Import Error", "Invalid file")
                return

            for j in i:
                if not isinstance(j, int):
                    logger.info("JSON contains invalid type!")
                    messagebox.showinfo("Import Error", "Invalid file")
                    return

            new_placements.append([i[0], i[1], bool(i[2])])

        if len(new_placements) < 3:
            logger.info("Load failed, not enough placements.")
            messagebox.showinfo("Import Error", "Invalid file")
            return

        self.placements.clear()
        self.placements.extend(new_placements)

        self.redraw_canvas()

    def background_tool_callback(self) -> None:
        """
        The callback for selecting a new background image
        :return: None
        """

        if self.workspace_canvas is None:
            logger.error("Cannot set background, GUI.workspace_canvas is None!")
            return

        filepath = Path(tkinter.filedialog.askopenfilename())
        if (
            not filepath
            or str(filepath) == "."
            or not filepath.exists(follow_symlinks=True)
        ):
            logger.info(f'No image at path "{filepath}"')
            return

        self.placements.clear()

        im = Image.open(filepath)
        im.close()
        self.im_path = filepath

        self.redraw_canvas()

    def workspace_click_callback(self, event) -> bool:
        """
        The callback that handles the workspace being clicked
        :param event: The click event
        :return: True on success False on fail.
        """

        if self.working_im is None:
            logger.debug("Cannot place nail as there is no image!")
            return False

        canvas_padding = 2
        x = event.x
        y = event.y

        im_in_bounds = (
            canvas_padding <= event.x <= self.working_im.width
            and canvas_padding <= event.y <= self.working_im.height
        )

        if not im_in_bounds:
            logger.debug(
                f"Cannot place nail at {x, y} as it is not on the image (width, height) = "
                f"{self.working_im.width, self.working_im.height}"
            )
            return False

        if self.active_tool == "Nail":
            logger.info(f"Placing nail on image at {x, y}")
            self.place_nail(x, y, priority=len(self.placements) == 0)
            return True

        if self.active_tool == "Erase":
            logger.info(f"Erasing nail on image at {x, y}")
            self.erase_nail(x, y)
            return True

        if self.active_tool == "Prioritize":
            logger.info(f"Setting priority nail to nail at {x, y}")
            self.prioritize_nail(x, y)
            return True

    def get_closest_nail(self, x: int, y: int) -> tuple[int, float]:
        """
        Returns the index and distance of the closest nail to a given x, y
        :param x: The x to check against
        :param y: The y to check against
        :return: A tuple with the index of the closest nail, and the distance to that nail.
        """

        def distance_to_nail(item: list[int, int, bool]) -> float:
            """
            Calculates the distance to a nail using the x, y passed to get_closest_nail.
            :param item: List with the nail x, y, and if it's the priority nail.
            :return: The distance to the nail
            """

            nail_x, nail_y, _ = item

            # distance = sqrt((x2-x1)^2+(y2-y1)^2)
            return math.sqrt(pow(nail_x - x, 2) + pow(nail_y - y, 2))

        # Sort the nails
        cloned = sorted(self.placements.copy(), key=distance_to_nail)

        if len(cloned) > 0:
            idx = self.placements.index(cloned[0])
            dist = distance_to_nail(self.placements[idx])
            return idx, dist

        # There is no nails, return a null value.
        return -1, -1.0

    def redraw_canvas(self):
        """
        Deletes the canvas element, and redraws the image and nails
        :return:
        """

        canvas_width, canvas_height = (
            self.workspace_canvas.winfo_width(),
            self.workspace_canvas.winfo_height(),
        )
        self.clear_canvas()

        im = Image.open(self.im_path)
        im = im.convert(mode="RGB")

        im_width, im_height = im.size
        im = scale_to_fit(im, canvas_width, canvas_height)

        self.im_scale = min(1.0, canvas_width / im_width)

        logger.info(f"Image Scale: {self.im_scale}")

        self.working_im = im
        tk_im = ImageTk.PhotoImage(self.working_im)

        self.workspace_frame.workspace_im = tk_im

        logger.info("Setting workspace canvas image")

        self.workspace_canvas.create_image(
            self.working_im.width // 2,
            0,
            anchor="n",
            image=tk_im,
        )

        for x, y, prioritized in self.placements:
            self.draw_nail(x, y, "#0f0f0f" if not prioritized else "#2fff2f")

    def erase_nail(self, x: int, y: int, safe_zone: int = 6) -> bool:
        """
        Erases a nail within the safe_zone
        :param x: x coordinate of the click
        :param y: y coordinate of the click
        :param safe_zone: The max distance from the nail to still count as being clicked
        :return: True on success, False on fail
        """

        closest_nail, dist = self.get_closest_nail(x, y)
        if closest_nail == -1:
            logger.debug(
                f"Failed to erase nail at {x, y} as there was no nails in GUI.placements!"
            )
            return False

        if dist > safe_zone:
            logger.debug(
                f"Failed to erase nail at {x, y} as the closest nail was {dist:.2f}px away!"
            )
            return False

        selected = self.placements.pop(closest_nail)

        if selected[2] and len(self.placements) > 0:
            self.placements[0][2] = True

        self.redraw_canvas()
        return True

    def place_nail(self, x: int, y: int, priority: bool = False) -> None:
        """
        Draws and adds a nail to the list
        :param x: The x coordinate to draw the nail at.
        :param y: The y coordinate to draw the nail at.
        :param priority: Whether the nail is the priority nail
        :return: None
        """
        if self.draw_nail(x, y, "#0f0f0f" if not priority else "#2fff2f"):
            self.placements.append([x, y, priority])

    def prioritize_nail(self, x: int, y: int, safe_zone: int = 6) -> bool:
        """
        Sets the priority nail.
        :param x: x coordinate of the nail
        :param y: y coordinate of the nail
        :param safe_zone: The max distance from the nail to still count as being clicked
        :return: True on success, False on failure
        """

        closest_nail, dist = self.get_closest_nail(x, y)
        if closest_nail == -1:
            logger.debug(
                f"Failed to prioritize nail at {x, y} as there was no nails in GUI.placements!"
            )
            return False

        if dist > safe_zone:
            logger.debug(
                f"Failed to prioritize nail at {x, y} as the closest nail is {dist:.2f}px away!"
            )
            return False

        self.placements[self.priority_nail][2] = False
        self.placements[closest_nail][2] = True
        self.priority_nail = closest_nail

        self.redraw_canvas()

    def draw_nail(self, x: int, y: int, color: str) -> bool:
        """
        Draws a nail on the canvas.
        :param x: x coordinate of the nail.
        :param y: y coordinate of the nail.
        :param color: Color of the nail (tkinter colors)
        :return:
        """
        if self.workspace_canvas is None:
            logger.warning("Cannot place a nail as there is no workspace_canvas!")
            return False

        # Draw the black outline
        self.workspace_canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#000000")
        # Draw the nail using the color
        self.workspace_canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color)
        return True

    def draw_toolbar(self) -> None:
        """
        Draws the toolbar for the application
        :return: None
        """

        # Make the frame for the toolbar
        frame = tk.Frame(master=self.root, height=90)
        frame.grid(row=0, column=0, columnspan=len(TOOLS), sticky="w")

        for k, tool in enumerate(TOOLS):
            item = tk.Button(master=frame, text=tool)
            item.config(command=functools.partial(self.tool_select_callback, k))
            item.grid(row=0, column=k)
            self.toolbar_widgets.append(item)

        seperator = tk.Frame(self.root, bg="#000000", height=1)
        seperator.grid(row=1, column=0, columnspan=len(TOOLS), sticky="ew")

    def clear_canvas(self) -> None:
        """
        Clears the canvas
        :return: None
        """

        self.workspace_canvas.destroy()

        canvas = tk.Canvas(master=self.workspace_frame)
        canvas.bind("<Button-1>", self.workspace_click_callback)
        canvas.pack(expand=True, fill="both", padx=0, pady=0)
        self.workspace_canvas = canvas

    def draw_workspace(self) -> None:
        """
        Draws the workspace frames
        :return: None
        """

        master_frame = tk.Frame(master=self.root)
        master_frame.grid(row=2, column=0, rowspan=10, columnspan=10, sticky="nsew")

        workspace_frame = tk.Frame(master=master_frame, bd=1, relief="solid")
        workspace_frame.pack(
            expand=True, fill="both", padx=WORKSPACE_PADDING, pady=WORKSPACE_PADDING
        )
        self.workspace_frame = workspace_frame

        canvas = tk.Canvas(master=workspace_frame)
        canvas.bind("<Button-1>", self.workspace_click_callback)
        canvas.pack(expand=True, fill="both", padx=0, pady=0)
        self.workspace_canvas = canvas

    def main_loop(self) -> None:
        self.root.mainloop()
