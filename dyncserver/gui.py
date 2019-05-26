# noinspection PyPackageRequirements
import wx
from PIL import Image
from io import BytesIO
import constants


class DyncCFrame(wx.Frame):
    window_image_size = 750

    def __init__(self, *args, **kw):
        self.server = kw.pop("server")
        self.old_image_buffer = None
        self.paths_menuitem = None
        # ensure the parent's __init__ is called
        super(DyncCFrame, self).__init__(*args, **kw)

        ico = wx.Icon('resources/dync.ico', wx.BITMAP_TYPE_ICO)
        self.SetIcon(ico)

        # create a panel in the frame
        self.panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        # st = wx.StaticText(self.panel)
        # font = st.GetFont()
        # font.PointSize += 10
        # font = font.Bold()
        # st.SetFont(font)
        #
        # # Doesn't resize correctly without the ending whitespace. Bug in wxWidgets?
        # st.SetLabel("DynC Server ")
        #
        # vbox.Add(st, 1)

        # create a menu bar
        self.make_menu_bar()

        # and a status bar
        self.CreateStatusBar()
        self.SetStatusText("Server is running")

        self.map = wx.StaticBitmap(self.panel, -1, wx.NullBitmap, (0, 0), (DyncCFrame.window_image_size,
                                                                           DyncCFrame.window_image_size))
        vbox.Add(self.map, 1)

        self.log_control = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.log_control.write("Game log:\n\n")
        vbox.Add(self.log_control, 1, wx.EXPAND)

        self.panel.SetSizer(vbox)
        self.panel.Layout()

    def update_log(self, contents):
        self.log_control.write(contents + "\n")

    def update_map(self, img_buffer):
        img_resized_buf = BytesIO()
        img_buffer.seek(0)
        img = Image.open(img_buffer)
        img_buffer.seek(0)
        img = img.resize((DyncCFrame.window_image_size, DyncCFrame.window_image_size), Image.LANCZOS)
        img.save(img_resized_buf, format="png")
        img_resized_buf.seek(0)
        png = wx.Image(img_resized_buf, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        img_resized_buf.close()

        self.map.SetBitmap(png)
        if self.old_image_buffer is not None:
            self.old_image_buffer.close()
        self.old_image_buffer = img_buffer
        self.panel.Layout()

    def make_menu_bar(self):
        """
        A menu bar is composed of menus, which are composed of menu items.
        This method builds a set of menus and binds handlers to be called
        when the menu item is selected.
        """

        # Make a file menu with Hello and Exit items
        file_menu = wx.Menu()
        # The "\t..." syntax defines an accelerator key that also triggers
        # the same event
        config_item = file_menu.Append(-1, "&Choose config\tCtrl-C", "Choose the .cfg file you want to use")
        self.paths_menuitem = file_menu.Append(-1, "Display &paths\tCtrl-P", "Display unit paths on map",
                                               kind=wx.ITEM_CHECK)
        img_item = file_menu.Append(-1, "&Save png\tCtrl-S", "Save the current map to a png")
        resetcampaign_item = file_menu.Append(-1, "&Reset campaign\tCtrl-R", "Reset the current campaign")
        file_menu.AppendSeparator()
        # When using a stock ID we don't need to specify the menu item's
        # label
        exit_item = file_menu.Append(wx.ID_EXIT)

        # Now a help menu for the about item
        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT)

        # Make the menu bar and add the two menus to it. The '&' defines
        # that the next letter is the "mnemonic" for the menu item. On the
        # platforms that support it those letters are underlined and can be
        # triggered from the keyboard.
        menu_bar = wx.MenuBar()
        menu_bar.Append(file_menu, "&File")
        menu_bar.Append(help_menu, "&Help")

        # Give the menu bar to the frame
        self.SetMenuBar(menu_bar)

        # Finally, associate a handler function with the EVT_MENU event for
        # each of the menu items. That means that when that menu item is
        # activated then the associated handler function will be called.
        self.Bind(wx.EVT_MENU, self.on_config, config_item)
        self.Bind(wx.EVT_MENU, self.on_paths, self.paths_menuitem)
        self.Bind(wx.EVT_MENU, self.on_save, img_item)
        self.Bind(wx.EVT_MENU, self.on_reset_campaign, resetcampaign_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        self.Bind(wx.EVT_MENU, DyncCFrame.on_about, about_item)

    def on_exit(self, _):
        self.Close(True)

    def on_config(self, _):
        open_file_dialog = wx.FileDialog(self, "Open", "", "", "Config files (*.cfg)|*.cfg",
                                         wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        open_file_dialog.ShowModal()
        self.server.read_config(open_file_dialog.GetPath())
        open_file_dialog.Destroy()

    def on_save(self, _):
        self.server.save_image()

    def on_reset_campaign(self, _):
        self.server.reset_campaign()

    def on_paths(self, _):
        self.server.display_map_paths = self.paths_menuitem.IsChecked()
        self.server.campaign_changed()

    @staticmethod
    def on_about(_):
        wx.MessageBox("DynC Server (version %s) by Markku Koponen" % constants.app_version,
                      "About DynC Server", wx.OK | wx.ICON_INFORMATION)
