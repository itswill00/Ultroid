<p align="center">
  <img src="../resources/extras/logo_readme.jpg" width="150" alt="Ultroid Logo">
</p>

<h1 align="center">Ultroid Addons</h1>

<p align="center">
  <b>Extended utility modules and community-driven features for the Ultroid Framework.</b>
</p>

---

### 🔱 About Addons

Addons are external plugins that extend the core functionality of Ultroid. They are loaded dynamically from this directory and can be managed (installed, updated, or removed) directly from the Telegram interface.

### 🤝 Contributing

We welcome community contributions. To ensure stability and maintainability, please follow these technical guidelines when submitting a pull request:

1. **Verify Functionality**: Always test your module in a live environment before submission.
2. **Metadata Header**: Include appropriate credits and source information at the top of your file:
   ```python
   # Credits: @username
   # Source: [Link if ported]
   # Refactored for Ultroid: https://github.com/itswill00/Ultroid
   ```
3. **Async Standard**: All modules must utilize `asyncio` patterns correctly.
4. **Dependencies**: If your addon requires additional Python packages, add them to `requirements.txt` in the root directory.

### 💻 Module Examples

#### **Standard Command**
```python
@ultroid_cmd(pattern="hello")
async def hello_world(event):
    await event.eor("Hello. I am active and responsive.")
```

#### **Group-Restricted Command**
```python
@ultroid_cmd(pattern="status", groups_only=True)
async def group_status(event):
    await event.eor("Group analytics synchronized.")
```

---
<p align="center">
  <i>Maintained by <a href="https://github.com/itswill00">itswill00</a> & the Ultroid community.</i>
</p>
