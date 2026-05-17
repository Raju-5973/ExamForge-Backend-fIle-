import os
import django
import random

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'examforge_backend.settings')
django.setup()

from questions.models import Question
from django.contrib.auth.models import User

def populate():
    # Get or create a user to associate questions with
    try:
        user = User.objects.get(username='RAJU')
    except User.DoesNotExist:
        user = User.objects.first()
    
    if not user:
        print("No users found in database. Please create a user first.")
        return

    data = [
        {
            'department': 'Computer Science',
            'subjects': {
                'Data Structures': [
                    ('What is a linked list?', 'Easy', 2, 'Lists', 'basic,ds'),
                    ('Explain the difference between a stack and a queue.', 'Medium', 5, 'Stacks & Queues', 'ds,fundamental'),
                    ('Write an algorithm to reverse a binary tree.', 'Hard', 10, 'Trees', 'algo,hard'),
                    ('What is the time complexity of binary search?', 'Easy', 2, 'Searching', 'complexity,basic'),
                    ('Explain the working of a Hash Table.', 'Medium', 5, 'Hashing', 'ds,search'),
                ],
                'Operating Systems': [
                    ('What is a process?', 'Easy', 2, 'Process Management', 'os,basic'),
                    ('Explain the difference between paging and segmentation.', 'Medium', 5, 'Memory Management', 'os,memory'),
                    ('What is a deadlock and how can it be prevented?', 'Hard', 10, 'Concurrency', 'os,deadlock'),
                    ('Explain the concept of Virtual Memory.', 'Medium', 5, 'Memory Management', 'os,memory'),
                    ('What is a system call?', 'Easy', 2, 'Kernel', 'os,basic'),
                ]
            }
        },
        {
            'department': 'Electrical',
            'subjects': {
                'Circuit Theory': [
                    ("State Ohm's Law.", 'Easy', 2, 'Basics', 'circuits,basic'),
                    ('What is KCL and KVL?', 'Medium', 5, 'Network Laws', 'circuits,laws'),
                    ('Explain the Superposition Theorem with an example.', 'Hard', 10, 'Theorems', 'circuits,advanced'),
                    ('Define Power Factor.', 'Easy', 2, 'AC Circuits', 'electrical,power'),
                    ('Calculate the equivalent resistance of a delta-star network.', 'Medium', 5, 'Network Transformation', 'circuits,math'),
                ],
                'Control Systems': [
                    ('What is an open-loop control system?', 'Easy', 2, 'Basics', 'control,intro'),
                    ('Explain the Routh-Hurwitz stability criterion.', 'Hard', 10, 'Stability', 'control,math'),
                    ('What is a Transfer Function?', 'Medium', 5, 'Modeling', 'control,basics'),
                ]
            }
        },
        {
            'department': 'Mechanical',
            'subjects': {
                'Thermodynamics': [
                    ('State the First Law of Thermodynamics.', 'Easy', 2, 'Laws', 'thermal,basics'),
                    ('Explain the Carnot Cycle.', 'Medium', 5, 'Cycles', 'thermal,engine'),
                    ('What is Entropy? Discuss its physical significance.', 'Hard', 10, 'Entropy', 'thermal,advanced'),
                ],
                'Fluid Mechanics': [
                    ("What is Bernoulli's equation?", 'Medium', 5, 'Fluid Dynamics', 'fluids,physics'),
                    ('Define Viscosity.', 'Easy', 2, 'Properties', 'fluids,basic'),
                ]
            }
        },
        {
            'department': 'Civil',
            'subjects': {
                'Structural Analysis': [
                    ('What is a truss?', 'Easy', 2, 'Basics', 'civil,structure'),
                    ('Explain the method of joints for truss analysis.', 'Medium', 5, 'Methods', 'civil,analysis'),
                    ('Define Moment Distribution Method.', 'Hard', 10, 'Indeterminate Structures', 'civil,advanced'),
                ],
                'Surveying': [
                    ('What is contouring?', 'Easy', 2, 'Basics', 'civil,survey'),
                    ('Explain the principle of Triangulation.', 'Medium', 5, 'Principles', 'civil,survey'),
                ]
            }
        },
        {
            'department': 'Electronics',
            'subjects': {
                'Digital Electronics': [
                    ('Draw the truth table for an XOR gate.', 'Easy', 2, 'Logic Gates', 'digital,basics'),
                    ('What is a Flip-Flop? List its types.', 'Medium', 5, 'Sequential Circuits', 'digital,memory'),
                    ('Design a 4-bit synchronous counter.', 'Hard', 10, 'Counters', 'digital,design'),
                ],
                'Microprocessors': [
                    ('What is an interrupt?', 'Easy', 2, 'Architecture', 'micro,basics'),
                    ('Explain the architecture of 8085 microprocessor.', 'Medium', 5, '8085', 'micro,arch'),
                ]
            }
        }
    ]

    count = 0
    for dept_info in data:
        dept_name = dept_info['department']
        for subject, questions in dept_info['subjects'].items():
            for q_text, difficulty, marks, sub_topic, tags in questions:
                Question.objects.get_or_create(
                    text=q_text,
                    subject=subject,
                    difficulty=difficulty,
                    marks=marks,
                    sub_topic=sub_topic,
                    tags=tags,
                    department=dept_name,
                    created_by=user
                )
                count += 1

    print(f"Successfully added {count} sample questions across {len(data)} departments.")

if __name__ == '__main__':
    populate()
