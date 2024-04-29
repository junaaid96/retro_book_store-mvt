# RetroBookStore - A Library Management System

## Overview

Live Link: https://retro-book-store.onrender.com

This project implements a system for managing books and user accounts. It allows users to browse, borrow, and review books, while also providing functionalities for user registration, login, logout, depositing money, and tracking borrowing history.

## Functionalities

### 1. Books

- Each book is characterized by its title, description, image, borrowing price, and user reviews.
- Books are categorized to enable users to filter them based on categories.

### 2. User

- Users can create accounts by providing necessary details.
- Secure login and logout processes are implemented.
- Users can borrow and return books, with the borrowing amount deducted from their account balance.
- Upon successful completion of a deposit or borrowing transaction, email notifications are sent to the user.
- Users can deposit money into their accounts, and the balance is used for borrowing books.
- Borrowing history, including borrowing dates, is tracked and displayed in the user's profile.
- Users can review books they have borrowed.
- When returning books, the borrowed amount is refunded to the user's account.

## Technologies Used

- HTML, CSS, Tailwind CSS, Python, Django, SQLite based on default MVT pattern.
